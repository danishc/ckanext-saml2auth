"""
Copyright (c) 2020 Keitaro AB

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import sys
# import hashlib
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extensions import AsIs
from sqlalchemy.engine.url import make_url

new_db_conn_str = os.environ.get('DB_SQLALCHEMY_URL', '')

master_user = os.environ.get('PSQL_MASTER_USER', '')
master_passwd = os.environ.get('PSQL_MASTER_PASSWORD', '')
master_database = os.environ.get('PSQL_MASTER_DB', '')
ckan_database = os.environ.get('CKAN_DB', '')


class DB_Params:
    def __init__(self, conn_str):
        self.db_user = make_url(conn_str).username
        self.db_passwd = make_url(conn_str).password
        self.db_host = make_url(conn_str).host
        self.db_name = make_url(conn_str).database


def check_db_connection(db_params, retry=None):

    print('Checking whether database is up...')

    if retry is None:
        retry = 20
    elif retry == 0:
        print('Giving up...')
        sys.exit(1)

    try:
        con = psycopg2.connect(user=master_user,
                               host=db_params.db_host,
                               password=master_passwd,
                               database=master_database)

    except psycopg2.Error as e:
        print((str(e)))
        print('Unable to connect to the database...try again in a while.')
        import time
        time.sleep(30)
        check_db_connection(db_params, retry=retry - 1)
    else:
        con.close()


def create_user(db_params):
    con = None
    try:
        con = psycopg2.connect(user=master_user,
                               host=db_params.db_host,
                               password=master_passwd,
                               database=master_database)
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        db_user = db_params.db_user.split("@")[0]
        print("Creating user " + db_user)
        # if user exist throw exception
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname='%s'" %(db_user))
        if cur.rowcount > 0:
            raise Exception("User already exist")
        cur.execute('CREATE ROLE "%s" ' +
                    'WITH ' +
                    'LOGIN NOSUPERUSER INHERIT ' +
                    'CREATEDB NOCREATEROLE NOREPLICATION ' +
                    'PASSWORD %s',
                    (AsIs(db_params.db_user.split("@")[0]),
                     db_params.db_passwd,))
                    # hashlib.md5(str(db_params.db_passwd).encode('utf-8')).hexdigest(),))
    except(Exception, psycopg2.DatabaseError) as error:
        print("ERROR DB: ", error)
    finally:
        cur.close()
        con.close()


def create_db(db_params):
    con = None
    try:
        con = psycopg2.connect(user=master_user,
                               host=db_params.db_host,
                               password=master_passwd,
                               database=master_database)
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        cur.execute('SELECT datname FROM pg_database;')
        list_database = cur.fetchall()
        if (db_params.db_name,) in list_database:
            raise Exception("'{}' Database already exist, no need to create again".format(db_params.db_name))
        cur.execute('GRANT "' + db_params.db_user.split("@")
                    [0] + '" TO "' + master_user.split("@")[0] + '"')
        print("Creating database " + db_params.db_name + " with owner " +
              db_params.db_user.split("@")[0])
        cur.execute('CREATE DATABASE ' + db_params.db_name + ' OWNER "' +
                    db_params.db_user.split("@")[0] + '"')
        cur.execute('GRANT ALL PRIVILEGES ON DATABASE ' +
                    db_params.db_name + ' TO "' +
                    db_params.db_user.split("@")[0] + '"')
        if is_pg_buffercache_enabled(db_params) >= 1:
            # FIXME: This is a known issue with pg_buffercache access
            # For more info check this thread:
            # https://www.postgresql.org/message-id/21009351582737086%40iva6-22e79380f52c.qloud-c.yandex.net
            print("Granting privileges on pg_monitor to " +
                  db_params.db_user.split("@")[0])
            cur.execute('GRANT "pg_monitor" TO "' + db_params.db_user.split("@")[0] + '"')
    except(Exception, psycopg2.DatabaseError) as error:
        print("ERROR DB: ", error)
    finally:
        cur.close()
        con.close()


def create_spatial_tables(db_params):
    con_master = None
    con_ckan = None
    try:
        # connect to master db to check if ckan db exist
        con_master = psycopg2.connect(user=master_user,
                               host=db_params.db_host,
                               password=master_passwd,
                               database=master_database)
        con_master.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur_master = con_master.cursor()
        cur_master.execute('SELECT datname FROM pg_database;')
        list_database = cur_master.fetchall()
        if (ckan_database,) not in list_database:
            raise Exception("'{}' DB is not ckan_default, no need to create spatial tables.".format(db_params.db_name))
        print("CKAN DB name: '{}' exist, trying to connect".format(db_params.db_name))
        # connect to ckan db as master user
        con_ckan = psycopg2.connect(user=master_user,
                                      host=db_params.db_host,
                                      password=master_passwd,
                                      database=ckan_database)
        cur_ckan = con_ckan.cursor()
        print("CKAN DB name: '{}': connection successful".format(db_params.db_name))
        # check if Postgis already installed
        cur_ckan.execute("select * from information_schema.tables where table_name=%s", ('spatial_ref_sys',))
        if not bool(cur_ckan.rowcount):
            print("PostGIS doesnot exist trying to create a tables using postgis-3.1 scripts")
            # enable PostGIS
            cur_ckan.execute(open("/usr/share/postgresql/contrib/postgis-3.1/postgis.sql", "r").read())
            cur_ckan.execute(open("/usr/share/postgresql/contrib/postgis-3.1/spatial_ref_sys.sql", "r").read())
            # Change the owner of spatial tables to the CKAN user
            cur_ckan.execute('ALTER VIEW geometry_columns OWNER TO "' + db_params.db_user.split("@")[0] + '"')
            cur_ckan.execute('ALTER TABLE spatial_ref_sys OWNER TO "' + db_params.db_user.split("@")[0] + '"')
            print(cur_ckan.execute("SELECT postgis_full_version()"))
        else:
            print("PostGIS already installed with a table \"spatial_ref_sys\" ")

    except(Exception, psycopg2.DatabaseError) as error:
        print("ERROR DB: ", error)
    finally:
        cur_ckan.close()
        con_ckan.close()
        cur_master.close()
        con_master.close()



def is_pg_buffercache_enabled(db_params):
    con = None
    result = None
    try:
        con = psycopg2.connect(user=master_user,
                               host=db_params.db_host,
                               password=master_passwd,
                               database=db_params.db_name)
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        cur.execute("SELECT count(*) FROM pg_extension " +
                    "WHERE extname = 'pg_buffercache'")
        result = cur.fetchone()
    except(Exception, psycopg2.DatabaseError) as error:
        print("ERROR DB: ", error)
    finally:
        cur.close()
        con.close()
    return result[0]

print('starting db init')

if master_user == '' or master_passwd == '' or master_database == '':
    print("No master postgresql user provided.")
    print("Cannot initialize default DB resources. Exiting!")
    sys.exit(1)

print("Master DB: " + master_database + " Master User: " + master_user)

new_db = DB_Params(new_db_conn_str)

# Check to see whether we can connect to the database, exit after 10 mins
check_db_connection(new_db)

try:
    create_user(new_db)
except(Exception, psycopg2.DatabaseError) as error:
    print("ERROR DB: ", error)

try:
    create_db(new_db)
except(Exception, psycopg2.DatabaseError) as error:
    print("ERROR DB: ", error)

try:
    create_spatial_tables(new_db)
except(Exception, psycopg2.DatabaseError) as error:
    print("ERROR DB: ", error)
