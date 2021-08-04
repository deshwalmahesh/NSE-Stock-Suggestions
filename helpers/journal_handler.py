import gspread
from oauth2client.service_account import ServiceAccountCredentials
from .investing import *
from .datahandler import *
from os import remove
import pandas as pd

all_listed_stocks = DataHandler.read_data()['all_stocks']
current_date = pd.to_datetime(date.today())

class JournalHandler:
    def __init__(self, key_file:str='client_sec.json', call_reminder:bool = True):
        '''
        Read the journal that you have used to track your investments directy from Google Drive using Google API and Credential
        args:
            key_file: json file which holds your secret key
            call_reminder: Whether to call the functions which remind you of important statistics at the time of instantiating the class
        '''
        scope = 'https://www.googleapis.com/auth/drive' #['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(key_file, scope)
        self.gs = gspread.authorize(creds)
        self.journal = None

        if call_reminder:
            self.journal = self.get_journal()
            self.check_21_days_rule(self.journal)
            self.analyse_future_profit(self.journal, all_listed_stocks)
        

    def get_journal(self,excel_file_name:str='Finance Journal',working_sheet_name:str='Real Trades'):
        '''
        Open the desired Google Sheet
        args:
            excel_file_name: Name of the Excel File
            working_sheet_name: Name of the Exact you want to open
        '''
        if isinstance(self.journal, pd.DataFrame):
            return self.journal

        gsheet = self.gs.open(excel_file_name)
        wsheet = gsheet.worksheet(working_sheet_name)
        df = pd.DataFrame(wsheet.get_all_records())

        df.to_csv('csvfile.csv', encoding='utf-8', index=False)
        df = pd.read_csv('csvfile.csv')
        df.dropna(subset=['Entry'],inplace = True)
        df['Buy Date'] = pd.to_datetime(df['Buy Date'])
        df['Exit Date'] = pd.to_datetime(df['Exit Date'])

        df.reset_index(drop=True,inplace=True)
        remove('csvfile.csv')
        return df


    def analyse_future_profit(self, journal, all_stocks:dict, data_path = './data/', High = 'HIGH', Close = 'CLOSE'):
        '''
        Analyse the stocks where you can get some Extra profit by changing the Profit trigger as Stop Loss Trigger
        args:
            journal: Journal DataFrame which keeps tab of your buying and selling sheet
            all_stocks: Dictonary which has {ID: Path of DataFrame}
            data_path: Path where your downloaded files are stored
            High: Columns name which describe HIGH of the stock
            Close: Columns name which describe Close of the stock
        '''
        active = journal[(journal['Exit Price'].isna()) & (journal['Exit Price'].isna())]

        results = []
        for i,val in enumerate(active.index):
            name = active.loc[val,'Stock Name']
            buy_date = active.loc[val,'Buy Date']
            target = active.loc[val,'Target']

            df = pd.read_csv(join(data_path,all_stocks[name]))

            last_high = df.loc[0,High]
            last_close = df.loc[0,Close]

            limit = target - (0.0175 * target)
            if (target > last_high) and (last_high > limit):
                results.append((name,buy_date))

        if len(results):
            print('These Stocks can give you extra profit by moving the Stop Loss as Target once Target is about to be triggered. Keep a track of these:','\n')
            for val in results:
                print(f"{val[0]} bought on: {val[1]},\n")
        print('-'*75,'\n')


    
    def check_21_days_rule(self,journal):
        '''
        If a stock was bought 21 days ago and still hasn't reached it's Target, Try selling it at 1:1.5 or 1:1 or current price
        args:
            journal: Dataframe of journal
        '''
        results = []
        for index,val in enumerate(journal.index):
            buy_date = journal.loc[val,'Buy Date']
            name = journal.loc[val,'Stock Name']
            if (current_date - journal.loc[1,'Buy Date']).days >= 21:
                results.append((name,buy_date))
        if len(results):
            print('These stocks have crossed 21 days limit. Sell them at 1:1.5 or 1:1 or at Market Price')

            for item in results:
                print(f"{item[0]} bought on {item[1]}\n")

        print('-'*75,'\n')
    