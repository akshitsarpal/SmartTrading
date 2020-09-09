import mysql.connector
from os import environ
from pdb import set_trace
from libs.st_logger.logger import logger


class DBWrapper(object):
    
    def __init__(self, db=None):
        self.db = db
        self.con = None
        self.cursor = None
        self.logger = logger('DBWrapper')
    
    
    def create_connection(self):
        if self.db:
            self.con = mysql.connector.connect(user=environ['db_user'], password=environ['db_pwd'],
                                          host='127.0.0.1', db=self.db)
        else:
            self.con = mysql.connector.connect(user=environ['db_user'], password=environ['db_pwd'],
                                          host='127.0.0.1')
        self.cursor = self.con.cursor()

        
    def executeReadQuery(self, query):
        try:
            self.create_connection()
            self.cursor.execute(query)
            dat = self.cursor.fetchall()
            cols = [column[0] for column in self.cursor.description]
            df = pd.DataFrame(dat, columns=cols)
        except:
            raise Exception('Could not read data from MySQL.')
        finally:
            self.con.close()
        return df
    
    
    def executeWriteQuery(self, df, table, index=False):
        try:
            self.create_connection()
            if index:
                df.reset_index(inplace=True)
            cols = "`,`".join([str(i) for i in df.columns.tolist()])
            update_values = ", ".join(["`"+str(i)+"`= new.`"+str(i)+"`" for i in df.columns.tolist()])
            for index, row in df.iterrows():
                query = '''INSERT INTO {table} (`{cols}`)
                VALUES {row} as new
                ON DUPLICATE KEY UPDATE {uv}
                '''.format(table=table, cols=cols, row=tuple(row.values), uv=update_values)
                self.cursor.execute(query)
                self.con.commit()
            self.logger.info('''Successfully inserted {r} rows to {table}
            '''.format(r=df.shape[0],table=table))
        except:
            raise Exception('Could not write data to MySQL.')
        finally:
            self.con.close()
            
            
    def executeQuery(self, query):
        try:
            self.create_connection()
            self.cursor.execute(query)
            self.con.commit()
        except:
            raise ValueError('Could not read data from MySQL.')
        finally:
            self.con.close()
