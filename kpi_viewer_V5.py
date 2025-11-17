from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as Navi
from matplotlib.figure import Figure
from matplotlib import dates as mdates
from matplotlib import ticker
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import TableModelWidget
import mplcursors
import csv
from PyQt5 import uic, sip, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QActionGroup, QMessageBox, QSizePolicy
import os
import re


matplotlib.use('Qt5Agg')


class MatplotlibCanvas(FigureCanvasQTAgg):
    '''Class for initializing Matplotlib canvas on Pytq interface'''
    def __init__(self, parent=None, dpi=120, mode="General"):
        self.fig = Figure(dpi = dpi)
        #depending on mode create one or two subplots
        if mode=="LTE RTWP"or mode=='Dual':
            self.axes= self.fig.add_subplot(211)
            self.axes2= self.fig.add_subplot(212, sharex=self.axes)
        else:
            self.axes= self.fig.add_subplot(111)
        self.fig.set_tight_layout(True)
        self.fig.autofmt_xdate()
        super(MatplotlibCanvas, self).__init__(self.fig)
        

class Window(QMainWindow):
    '''Window is the main class to show de window aplication and all its components'''
    def __init__(self):
        super().__init__()
        uic.loadUi("kpi_viewer5.ui", self) #loads UI from file
        self.kpis_info_csv= self.resource_path('KPIS_data.csv') #Path to KPI information CSV
        self.initial_vars() #Initialize all variables
        self.canv = MatplotlibCanvas(self, mode="General") #Create Matplotlib canvas
        try:
            self.kpi_info=pd.read_csv(self.kpis_info_csv, sep=';', index_col='KPI Alias') #Load KPI information from CSV
        except Exception as e:
            print(e)
            self.textBrowser.append('Error, missing file KPI_INFO.csv')
        # Set up all signals and slots    
        self.radio_850.setEnabled(False)
        self.radio_850.toggled.connect(self.filter_band)
        self.radio_1900.setEnabled(False)
        self.radio_1900.toggled.connect(self.filter_band)
        self.radio_2600.setEnabled(False)
        self.radio_2600.toggled.connect(self.filter_band)
        self.radio_700.setEnabled(False)
        self.radio_700.toggled.connect(self.filter_band)
        self.radio_all.setEnabled(False)
        self.radio_all.setChecked(True)
        self.radio_all.toggled.connect(self.filter_band)
        self.themes = ['bmh', 'classic', 'dark_background', 'fast',
		'fivethirtyeight', 'ggplot', 'grayscale', 'seaborn-bright',
		 'seaborn-colorblind', 'seaborn-dark-palette', 'seaborn-dark',
         'seaborn-darkgrid', 'seaborn-deep', 'seaborn-muted', 'seaborn-notebook',
		 'seaborn-paper', 'seaborn-pastel', 'seaborn-poster', 'seaborn-talk',
		 'seaborn-ticks', 'seaborn-white', 'seaborn-whitegrid', 'seaborn',
		 'Solarize_Light2', 'tableau-colorblind10']
        self.comboBox.addItems(self.themes)
        self.comboBox.setCurrentText('seaborn-notebook')
        self.comboBox.currentIndexChanged['QString'].connect(self.prepare_canvas)
        self.list_eb.itemClicked.connect(self.get_list_item)
        self.list_plots.currentItemChanged.connect(self.kpi_select)
        self.btn_load.clicked.connect(self.get_file_path)
        self.btn_plot.clicked.connect(self.clicked_plot_button)
        self.btn_clear.clicked.connect(self.clicked_clear_button)
        self.checkBox.toggled.connect(self.build_table)
        self.checkBox_2.toggled.connect(self.update_plots_list)
        self.checkBox_2.setEnabled(False)
        self.toolbar = Navi(self.canv,self.centralwidget)
        self.horizontalLayout_2.addWidget(self.toolbar)
        self.actionSalir.triggered.connect(self.close)
        self.actionAbrir.triggered.connect(self.get_file_path)
        self.action_group = QActionGroup(self)
        self.action_group.addAction(self.actionGeneral)
        self.action_group.addAction(self.actionLTE_Rtwp)
        self.action_group.addAction(self.actionUMTS_Prach)
        self.action_group.addAction(self.actionDual)
        self.actionGeneral.triggered.connect(self.set_mode)
        self.actionLTE_Rtwp.triggered.connect(self.set_mode)
        self.actionUMTS_Prach.triggered.connect(self.set_mode)
        self.actionDual.triggered.connect(self.set_mode)

    #FUNCTIONS
    def initial_vars(self):
        '''Initialize all variables used in the program'''
        self.is_updating=True
        self.files=[]
        self.nodeb=''  
        self.tec_name='' 
        self.cell_name=''
        self.filename = ''
        self.df_gsm = []
        self.df_umts = []
        self.df_lte = []
        self.df_antl=[]
        self.kpi_index=0
        self.kpi2_index=0
        self.kpi_all=[]
        self.kpi_700=[]
        self.kpi_850=[]
        self.kpi_1900=[]
        self.kpi_2600=[]
        self.plot_names=[]
        self.band='All'
        self.enodebs=[]
        self.antdif_plots=[]
        self.mode='General'
        self.current_sel=pd.DataFrame()
        self.current_sel2=pd.DataFrame()


    def resource_path(self, relative_path):
        '''Get absolute path to resource for creating executable with PyInstaller'''
        try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)


    def set_mode(self):
        '''Set plotting mode from menu'''
        self.mode=self.sender().text()

    def update_plots_list(self):
        '''Update list of Kpi plots'''
        self.is_updating=True
        if self.checkBox_2.isChecked():
            self.list_plots.setCurrentRow(self.kpi2_index)
        else:
            self.list_plots.setCurrentRow(self.kpi_index)
        self.is_updating=False

    def get_file_path(self):
        '''function to get the path of xlsx/csv files and call the respective reading function'''
        try:
            self.filename = QFileDialog.getOpenFileName(filter = "xlsx/csv (*.xlsx *.csv)")[0]
            if self.filename not in self.files:
                self.files.append(self.filename)
                extension=self.filename[-4:]
                if extension=='xlsx':
                    self.read_xlsx_data()
                elif extension=='.csv':
                    self.read_csv_data()
            else:
                self.textBrowser.append("File ommited, previously loaded")
        except AssertionError:
            self.textBrowser.append("No file loaded")

    def read_csv_data(self):
        '''Function to read csv data files containing RTWP data, 
            the logic to manage exceptions for non expected data formating haven't been implemented
            therefore, I expect a proper file by now'''
        offset_l=0
        offset_w=0
        with open(self.filename,'rt')as f:
            data = csv.reader(f)
            index=0
            for row in data:
                if not row:
                    index +=1
                    continue
                if row[0]=='RTWP (dBm)':
                    offset_l=index
                if row[0]=='RSSI (dBm)':
                    offset_w=index
                index +=1
        rows_lte=offset_w-offset_l-3
        df4 = pd.read_csv(self.filename, header=offset_l,  nrows=rows_lte, index_col=[2,1])
        df4['Site']=df4.index.get_level_values(0).str[:-3]
        self.df_antl.append(df4)
        sites = df4['Site'].unique().tolist()
        self.update_list(sites, tec=' ANTL')
        self.textBrowser.append(f'Antenna Line monitoring csv file readed for site:{sites[0]}')
    

    def clicked_clear_button(self):
        '''Clear all data and variables'''
        self.initial_vars()
        self.radio_all.setEnabled(False)
        self.radio_850.setEnabled(False)
        self.radio_1900.setEnabled(False)
        self.radio_700.setEnabled(False)
        self.radio_2600.setEnabled(False)
        self.checkBox_2.setEnabled(False)
        self.list_eb.clear()
        self.list_plots.clear()
        self.is_updating=False
        self.prepare_canvas()
        self.textBrowser.clear()

    def clear_data(self):
        self.is_updating=True
        self.list_plots.clear()
        self.kpi_all=[]
        self.plot_names=[]
        self.kpi_index=0
        self.kpi2_index=0
        self.kpi_700=[]
        self.kpi_850=[]
        self.kpi_1900=[]
        self.kpi_2600=[]
        self.band='All'
        self.radio_all.setEnabled(False)
        self.radio_850.setEnabled(False)
        self.radio_1900.setEnabled(False)
        self.radio_700.setEnabled(False)
        self.radio_2600.setEnabled(False)
        self.checkBox_2.setEnabled(False)


    def clicked_plot_button(self):
        
        self.clear_data()
        if self.tec_name=='ANTL':
            self.actionGeneral.setChecked(True)
            self.plot_antl()
        else:
            self.prepare_data()

    def plot_antl(self):
        site_dfs=[]
        
        for df in self.df_antl:
            site=df['Site'].unique().tolist()
            if site[0]==self.nodeb:
                df=df.drop(['Site'], axis=1)
                try:
                    df=df.drop(['Radio Module'], axis=1)
                except:
                    df=df.drop(['Radio module'], axis=1)
                site_dfs.append(df)
        
        data=pd.concat(site_dfs, axis=1)
        cells= data.index.get_level_values(0).unique().tolist()
        data=data.T
        data.index = data.index.str.replace('=', '')
        data.index = data.index.str.replace('"', '')
        data=data.sort_index()
        
        for cell in cells:
            
            plot=data[cell].copy()
            try:
                plot['Ant Difference']=plot.max(axis=1) - plot.min(axis=1)
                self.kpi_all.append(plot)
            #plot.index.names=['Time']
            except:
                continue
            

        self.plot_names=cells
        self.list_plots.addItems(cells)
        self.is_updating=False
        self.prepare_canvas()


    def read_xlsx_data(self):
        """ This function will read the xlsx data using pandas"""
        try:
            excel_data = pd.read_excel(self.filename, index_col=0)
            excel_data = excel_data.drop(excel_data.index[0])
            excel_data = excel_data.infer_objects()
        except ValueError as _e:
            self.textBrowser.append(f'Error: {_e} ')
            return
        # Delete unuseful columns
        if 'PLMN name' in excel_data.columns:
            excel_data=excel_data.drop(['PLMN name'], axis=1)
            #self.textBrowser.append('"PLMN name" column deleted from input, not necesary for further processing')
        if 'MRBTS/SBTS name' in excel_data.columns:
            excel_data=excel_data.drop(['MRBTS/SBTS name'], axis=1)
            #self.textBrowser.append('"MRBTS/SBTS" column deleted from input, not necesary for further processing')
        if 'LNBTS type' in excel_data.columns:
            excel_data=excel_data.drop(['LNBTS type'], axis=1)
            #self.textBrowser.append('"LNBTS type" column deleted from input, not necesary for further processing')
        if 'WCEL name' in excel_data.columns:
            excel_data = excel_data.astype({"WBTS ID": str, "WCEL ID": str})
            excel_data.dropna(axis=1, how='all', inplace=True)
            excel_data.insert(excel_data.columns.get_loc("WCEL name") + 1, 'Band' ,excel_data['WCEL name'].apply(self.generate_band))
            self.df_umts.append(excel_data)
            sites = excel_data['WBTS name'].unique().tolist()
            tec='3G'
            self.update_list(sites, tec=' 3G')
        elif 'BTS name' in excel_data.columns:
            excel_data.insert(excel_data.columns.get_loc("BTS name") + 1, 'Band' ,excel_data['BTS name'].apply(self.generate_band))
            self.df_gsm.append(excel_data)
            sites = excel_data['BCF name'].unique().tolist()
            tec='2G'
            self.update_list(sites, tec=' 2G')
        elif 'LNCEL name' in excel_data.columns:
            excel_data.insert(excel_data.columns.get_loc('LNCEL name') + 1, 'Band', excel_data['LNCEL name'].apply(self.generate_band))
            if 'AVG_RTWP_RX_ANT_1 (M8005C306)' in list(excel_data):
                _cols=excel_data[['AVG_RTWP_RX_ANT_1 (M8005C306)','AVG_RTWP_RX_ANT_2 (M8005C307)',
                                      'AVG_RTWP_RX_ANT_3 (M8005C308)', 'AVG_RTWP_RX_ANT_4 (M8005C309)']]
                for col in _cols:
                    if _cols[col].isnull().all():
                        continue
                    excel_data[col] = excel_data[col].div(10)
                excel_data.rename(columns={'AVG_RTWP_RX_ANT_1 (M8005C306)':'Avg RWTP RX ant 1', 'AVG_RTWP_RX_ANT_2 (M8005C307)':'Avg RWTP RX ant 2',
                                           'AVG_RTWP_RX_ANT_3 (M8005C308)':'Avg RWTP RX ant 3', 'AVG_RTWP_RX_ANT_4 (M8005C309)':'Avg RWTP RX ant 4'}, inplace=True)
            if 'Avg RWTP RX ant 1' in list(excel_data):                               
                rtwp_cols=excel_data[['Avg RWTP RX ant 1','Avg RWTP RX ant 2', 'Avg RWTP RX ant 3', 'Avg RWTP RX ant 4']]
                excel_data.insert(excel_data.columns.get_loc("Avg RWTP RX ant 4") + 1, 'ANT Difference', rtwp_cols.max(axis=1) - rtwp_cols.min(axis=1))
            self.df_lte.append(excel_data)
            sites = excel_data['LNBTS name'].unique().tolist()
            tec='4G'
            self.update_list(sites, tec=' 4G')
        else:
            self.textBrowser.append('No valid data')
            return

        text = ', '.join(sites)
        date=pd.to_datetime(excel_data.index)
        date_i=date[0].strftime("%d-%b %H:%M")
        date_f=date[-1].strftime("%d-%b %H:%M")
        self.textBrowser.append(f'{tec} File readed: {text}, from {date_i}Hrs to {date_f}Hrs')


    def generate_band(self, cell):
        '''function to generate new column with the band depending on the sector input'''
        sector = cell[-2:]
        sectors_850=['_1', '_2', '_3', '_4', '_X', '_Y', '_Z', '_U','_V', '_W', 'Y1',
                    'Y2', 'Y3', 'Y4', 'Y5', 'Y6', 'X1', 'X2','X3','X4','X5','X6', 'S1', 'S2','S3', 'S4', 'S5', 'S6']
        sectors_1900=['_I', '_J', '_K', '_L', '_M', '_N','_O', '_P', '_Q','_R','_S',
                    '_T','M1','M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', '_A', '_B', '_C', '_D', '_E']
        sectors_700=['R1','R2','R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']
        sectors_2600=['L1','L2','L3','L4','L5','L6','T1','T2','T3','T4', 'T5', 'T6',  'T7', 'T8', 'T9', 'L7', 'L8', 'L9']
        if sector in sectors_850:
            return '850'
        elif sector in sectors_1900:
            return '1900'
        elif sector in sectors_2600:
            return '2600'
        elif sector in sectors_700:
            return '700'
        return 'Unknown sector'
    
    def update_list(self, sites, tec=None):
        '''Update the ListWidget containing all the sites readed in the input'''
        self.list_eb.clear()
        for site in sites:
            _eb = site + tec
            if _eb not in self.enodebs:
                self.enodebs.append(_eb)
        self.list_eb.addItems(self.enodebs)

    def get_list_item(self, item):
        'Function to get selected EB, technology and cell type'
        self.nodeb= item.text()[:-3]
        if item.text()[-2:]=='2G':
            self.tec_name='BCF name'
            self.cell_name='BTS name'
        elif item.text()[-2:]=='3G':
            self.tec_name='WBTS name'
            self.cell_name='WCEL name'
        elif item.text()[-2:]=='4G':
            self.tec_name='LNBTS name'
            self.cell_name='LNCEL name'
        elif item.text()[-2:]=='TL':
            self.tec_name='ANTL'
            self.cell_name='Site'
            self.nodeb= item.text()[:-5]

        if self.tec_name=='ANTL':
            self.actionLTE_Rtwp.setEnabled(False)
            self.actionUMTS_Prach.setEnabled(False)
            self.actionDual.setEnabled(False)
        else:
            self.actionLTE_Rtwp.setEnabled(True)
            self.actionUMTS_Prach.setEnabled(True)
            self.actionDual.setEnabled(True)
            
    def prepare_data(self):
        '''Prepare data to plot'''
        data_bands=[]
        data=pd.DataFrame()
        if self.tec_name=='LNBTS name':
            data= pd.concat(self.df_lte)
        elif self.tec_name=='WBTS name':
            data= pd.concat(self.df_umts)
        elif self.tec_name=='BCF name':
            data= pd.concat(self.df_gsm)
        elif self.tec_name=='':
            self.textBrowser.append("Please select a base station to plot")
            return
        data = data.drop_duplicates()
        data=data[data[self.tec_name].eq(self.nodeb)]
        sectors= data[self.cell_name].unique().tolist()

        if self.mode=='Dual':
            self.checkBox_2.setEnabled(True)
        if self.mode=='General' or self.mode=='Dual':
            data_bands = data['Band'].unique().tolist()
            self.radio_all.setChecked(True)
            self.radio_all.setEnabled(True)
            self.radio_850.setEnabled('850' in data_bands)
            self.radio_1900.setEnabled('1900' in data_bands)
            self.radio_700.setEnabled('700' in data_bands)
            self.radio_2600.setEnabled('2600' in data_bands)
            self.kpi_all = self.create_plots(data, self.cell_name)
            if '1900' in data_bands:
                data_1900=data[data['Band'].eq('1900')]
                self.kpi_1900 = self.create_plots(data_1900, self.cell_name)
            if '2600' in data_bands:
                data_2600=data[data['Band'].eq('2600')]
                self.kpi_2600 = self.create_plots(data_2600, self.cell_name)
            if '700' in data_bands:
                data_700=data[data['Band'].eq('700')]
                self.kpi_700 = self.create_plots(data_700, self.cell_name)
            if '850' in data_bands:
                data_850=data[data['Band'].eq('850')]
                self.kpi_850 = self.create_plots(data_850, self.cell_name)
            for kpi in list(data):
                if data.dtypes[kpi] !='O':
                    self.plot_names.append(kpi)
            
            self.list_plots.addItems(self.plot_names)
            self.is_updating=False
            self.prepare_plot()
        if self.mode=='LTE RTWP':
            if self.tec_name !='LNBTS name':
                pop_msg= QMessageBox()
                pop_msg.setWindowTitle("Warning")
                pop_msg.setText("Mode only valid for LTE data")
                pop_msg.setIcon(QMessageBox.Warning)
                _x = pop_msg.exec_()
                return
            rtwp_data=data[['LNCEL name', 'Avg RWTP RX ant 1','Avg RWTP RX ant 2', 'Avg RWTP RX ant 3', 'Avg RWTP RX ant 4']]
            antdif_data=data[['LNCEL name', 'ANT Difference']]
            self.plot_names = sectors
            
            self.list_plots.addItems(sectors)
            self.antdif_plots=[]
            for sector in sectors:
                _nn=rtwp_data[rtwp_data['LNCEL name'].eq(sector)]
                _ant=antdif_data[antdif_data['LNCEL name'].eq(sector)]
                self.kpi_all.append(_nn)
                self.antdif_plots.append(_ant)
            self.current_sel=self.kpi_all[self.kpi_index]
            self.current_sel2=self.antdif_plots[self.kpi_index]
            self.is_updating=False
            self.prepare_canvas()
        if self.mode=='UMTS PRACH':
            if self.tec_name !='WBTS name':
                pop_msg= QMessageBox()
                pop_msg.setWindowTitle("Warning")
                pop_msg.setText("Mode only valid for UMTS data")
                pop_msg.setIcon(QMessageBox.Warning)
                _x = pop_msg.exec_()
                return
            prach_data=data[['WCEL name', 'PRACH_DELAY_CLASS_0 (M1006C128)',
                            'PRACH_DELAY_CLASS_1 (M1006C129)', 'PRACH_DELAY_CLASS_2 (M1006C130)',
                            'PRACH_DELAY_CLASS_3 (M1006C131)', 'PRACH_DELAY_CLASS_4 (M1006C132)',
                            'PRACH_DELAY_CLASS_5 (M1006C133)', 'PRACH_DELAY_CLASS_6 (M1006C134)',
                            'PRACH_DELAY_CLASS_7 (M1006C135)', 'PRACH_DELAY_CLASS_8 (M1006C136)',
                            'PRACH_DELAY_CLASS_9 (M1006C137)', 'PRACH_DELAY_CLASS_10 (M1006C138)',
                            'PRACH_DELAY_CLASS_11 (M1006C139)', 'PRACH_DELAY_CLASS_12 (M1006C140)',
                            'PRACH_DELAY_CLASS_13 (M1006C141)', 'PRACH_DELAY_CLASS_14 (M1006C142)',
                            'PRACH_DELAY_CLASS_15 (M1006C143)']]
            self.plot_names = sectors
            
            self.list_plots.addItems(sectors)
            
            for sector in sectors:
                _nn=prach_data[prach_data['WCEL name'].eq(sector)]
                self.kpi_all.append(_nn)
            self.current_sel=self.kpi_all[self.kpi_index]
            self.is_updating=False
            self.prepare_canvas()

    def create_plots(self, df, cell_type):
        '''function that returns a pivot table for every kpi readed on the input'''
        plots_list=[]
        for column in list(df):
            if df.dtypes[column]=='O':
                continue
            kpi = pd.pivot_table(df, index=["Period start time"], values = column, columns=[cell_type])
            plots_list.append(kpi)
        return plots_list

    
    def kpi_select(self):
        '''Function for changing Plot from combo Box'''
      
        if self.is_updating:
            return
        
        else:
            if self.checkBox_2.isChecked():
                self.kpi2_index=self.list_plots.currentRow()
                self.prepare_plot()
            else:
                self.kpi_index=self.list_plots.currentRow()
                self.prepare_plot()

    def filter_band(self):
        '''filter band from check buttons'''
        if self.is_updating:
            return
        if self.sender().isChecked():
            self.band = self.sender().text()
        self.prepare_plot()

    def prepare_plot(self):
        '''prepare data before plotting function'''
        if self.mode=='General' or self.mode=='Dual':
            if self.band=='All':
                self.current_sel=self.kpi_all[self.kpi_index]
                self.current_sel2=self.kpi_all[self.kpi2_index]
            elif self.band=='850':
                self.current_sel=self.kpi_850[self.kpi_index]
                self.current_sel2=self.kpi_850[self.kpi2_index]
            elif self.band=='1900':
                self.current_sel=self.kpi_1900[self.kpi_index]
                self.current_sel2=self.kpi_1900[self.kpi2_index]
            elif self.band=='700':
                self.current_sel=self.kpi_700[self.kpi_index]
                self.current_sel2=self.kpi_700[self.kpi2_index]
            elif self.band=='2600':
                self.current_sel=self.kpi_2600[self.kpi_index]
                self.current_sel2=self.kpi_2600[self.kpi2_index]
        elif self.mode=='LTE RTWP':
            self.current_sel=self.kpi_all[self.kpi_index]
            self.current_sel2=self.antdif_plots[self.kpi_index]
        elif self.mode=='UMTS PRACH':
            self.current_sel=self.kpi_all[self.kpi_index]
        self.prepare_canvas()
        self.build_table()

    def build_table(self):
        '''Build table view from current selected data'''
        if self.checkBox.isChecked():
            model=TableModelWidget.TableModel(self.current_sel)
            self.tableView.setModel(model)
            self.tableView.setAlternatingRowColors(True)
            self.tableView.resizeColumnsToContents()
            self.tableView.resizeRowsToContents()
        else:
            self.tableView.setModel(None)

    def prepare_canvas(self):
        '''Prepare Matplotlib canvas before plotting'''
        if self.is_updating:
            return
        if self.checkBox_2.isChecked():
            self.list_plots.setCurrentRow(self.kpi2_index)
        else:
            self.list_plots.setCurrentRow(self.kpi_index)
        self.textBrowser_2.clear()
        try:
            plt.clf()
            plt.style.use(self.comboBox.currentText())
            self.horizontalLayout_2.removeWidget(self.toolbar)
            self.verticalLayout.removeWidget(self.canv)
            sip.delete(self.toolbar)
            sip.delete(self.canv)
            self.toolbar = None
            self.canv = None
        except TypeError:
            self.textBrowser.append("Something happened!")

        if self.tec_name=='':
            return
        elif self.tec_name=='ANTL':
            self.update_ant_plot()
        else:
            self.update_plot()


    def update_plot(self):
        '''Update plot Function'''
        
        self.canv = MatplotlibCanvas(self, mode=self.mode)
        #self.canv.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar = Navi(self.canv,self.centralwidget)
        self.horizontalLayout_2.addWidget(self.toolbar)
        self.verticalLayout.addWidget(self.canv)
        self.canv.axes.cla()
        day = mdates.DayLocator(interval = 1)
        locator = mdates.AutoDateLocator()
        #locator = mdates.DayLocator(interval = 1)
        formatter = mdates.ConciseDateFormatter(mdates.AutoDateLocator())
        
        
        title=self.plot_names[self.kpi_index]
        title2=self.plot_names[self.kpi2_index]
        axs = self.canv.axes
        axs.set_title(title)
        try:
            img = self.current_sel.plot(ax = axs, x_compat=True, kind= "line")
            #tick formatting
            axs.xaxis.set_minor_locator(day)
            axs.xaxis.set_major_locator(locator)
            axs.xaxis.set_major_formatter(formatter)
            axs.grid(True)
            axs.tick_params(axis='x', labelrotation = 90)
        except TypeError:
            self.textBrowser.append("No numeric data to plot")
            return
        _c1=mplcursors.cursor(img)
        lines = axs.get_lines()
        leg = axs.legend(bbox_to_anchor=(1.05 , 0.5), loc='center left', fancybox=True, shadow=True, frameon=True)
        lined = {}  # Will map legend lines to original lines.
        if self.mode=='General':
            current_item=title
            try:
                axs.set_ylabel(self.kpi_info.loc[title, 'Unit'])
                self.textBrowser_2.append(self.kpi_info.loc[title, 'KPI ID'])
                self.textBrowser_2.append(self.kpi_info.loc[title, 'Description'])
            except:
                self.textBrowser.append(f"Kpi Error : {title}")
                return
        elif self.mode=='Dual':
            current_item=title
            current_item2=title2
            axs2 = self.canv.axes2
            axs2.set_title(title2)
            try:
                img2=self.current_sel2.plot(ax = axs2, x_compat=True)
                axs2.xaxis.set_minor_locator(day)
                axs2.xaxis.set_major_locator(locator)
                axs2.xaxis.set_major_formatter(formatter)
                axs2.grid(True)
                axs2.tick_params(axis='x', labelrotation = 90)
            except TypeError:
                self.textBrowser.append("No numeric data to plot")
                return
            try:
                axs.set_ylabel(self.kpi_info.loc[title, 'Unit'])
            except:
                self.textBrowser.append(f"Dual mode, Error : {title}")
            try:
                axs2.set_ylabel(self.kpi_info.loc[title2, 'Unit'])
            except:
                self.textBrowser.append(f"Duel mode, Error: {title2}")
            _c2=mplcursors.cursor(img2)
            @_c2.connect("add")
            def _(sel2):
                date=mdates.DateFormatter("%d-%b %H:%M")(sel2.target[0])
                sel2.annotation.set_text('{}\n{}Hrs\n{:.2f}{}'.format(sel2.artist.get_label(), date,  sel2.target[1], self.kpi_info.loc[current_item2, 'Unit']))
                sel2.annotation.set(fontsize=8, ha="left")
                sel2.annotation.get_bbox_patch().set(fc="white", alpha=.5)
            lines2 = axs2.get_lines()
            leg2 = axs2.legend(bbox_to_anchor=(1.05 , 0.5), loc='center left', fancybox=True, shadow=True, frameon=True)
            lined2 = {}
            for legline2, origline2 in zip(leg2.get_lines(), lines2):
                legline2.set_picker(5)
                lined2[legline2] = origline2
            lined.update(lined2)
        elif self.mode=='UMTS PRACH':
            current_item='UMTS_PRACH_Sector'
            axs.set_ylabel('[#]')
        elif self.mode=='LTE RTWP':
            current_item='LTE_RTWP_SECTOR'
            current_item2='LTE_RTWP_SECTOR'
            axs2 = self.canv.axes2
            try:
                img2 = self.current_sel2.plot(ax = axs2, x_compat=True, drawstyle="steps-mid", kind= "line")
                _c2=mplcursors.cursor(img2)
            except TypeError:
                self.textBrowser.append("No numeric data to plot")
                _c2=mplcursors.cursor()
            #Thresholds
            axs.axhline(y=-92, color='r', alpha=0.4, linestyle='--', label='-92dBm')
            axs2.axhline(y=3, color='r', alpha=0.4, linestyle='--', label='3dBm')
            axs2.tick_params(axis='x', labelrotation = 90)
            #formatting
            axs.set_ylabel('dBm')
            axs2.set_title('ANT Difference')
            axs2.xaxis.set_minor_locator(day)
            axs2.xaxis.set_major_locator(locator)
            axs2.xaxis.set_major_formatter(formatter)
            axs2.set_ylabel('dBm')
            leg2=axs2.legend(bbox_to_anchor=(1.05 , 0.5), loc='center left', fancybox=True, shadow=True, frameon=True)
            axs2.grid(True)
            @_c2.connect("add")
            def _(sel2):
                date=mdates.DateFormatter("%d-%b %H:%M")(sel2.target[0])
                sel2.annotation.set_text('{}\n{}Hrs\n{:.2f}{}'.format(sel2.artist.get_label(), date,  sel2.target[1], self.kpi_info.loc[current_item2, 'Unit']))
                sel2.annotation.set(fontsize=8, ha="left")
                sel2.annotation.get_bbox_patch().set(fc="white", alpha=.5)
        @_c1.connect("add")
        def _(sel):
            date=mdates.DateFormatter("%d-%b %H:%M")(sel.target[0])
            sel.annotation.set_text('{}\n{}Hrs\n{:.2f}{}'.format(sel.artist.get_label(), date,  sel.target[1], self.kpi_info.loc[current_item, 'Unit'] ))
            sel.annotation.set(fontsize=8, ha="left")
            sel.annotation.get_bbox_patch().set(fc="white", alpha=.5)
            sel.annotation.arrow_patch.set(arrowstyle="simple", fc="white", )
        for legline, origline in zip(leg.get_lines(), lines):
            legline.set_picker(5)  # Enable picking on the legend line.
            lined[legline] = origline

        def on_pick(event):
            '''On the pick event, find the original line corresponding to the legend proxy line, and toggle its visibility'''
            legend_picked = event.artist
            if isinstance(legend_picked, matplotlib.lines.Line2D):
                origline = lined[legend_picked]
                visible = not origline.get_visible()
                origline.set_visible(visible)
                # Change the alpha on the line in the legend so we can see what lines have been toggled.
                legend_picked.set_alpha(1.0 if visible else 0.2)
                self.canv.draw()
        self.canv.mpl_connect('pick_event', on_pick)

    def update_ant_plot(self):
        '''Update ant plot Function'''
        self.canv = MatplotlibCanvas(self, mode='Dual')
        #self.canv.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar = Navi(self.canv,self.centralwidget)
        self.horizontalLayout_2.addWidget(self.toolbar)
        self.verticalLayout.addWidget(self.canv)
        self.canv.axes.cla()
        title=self.plot_names[self.kpi_index]
        self.current_sel=self.kpi_all[self.kpi_index].iloc[:,:-1]
        self.current_sel2=self.kpi_all[self.kpi_index]['Ant Difference']
        axs = self.canv.axes
        axs2 = self.canv.axes2
        axs.set_title(title)
        axs2.set_title('ANT Difference')
        img1=self.current_sel.plot(ax=axs)
        img2=self.current_sel2.plot(kind='bar', ax = axs2)
        axs.set_ylabel('dBm')
        axs2.set_ylabel('dBm')
        axs.grid(True)
        axs2.grid(True)
        axs.legend(bbox_to_anchor=(1.05 , 0.5), loc='center left', fancybox=True, shadow=True, frameon=True)
        axs2.tick_params(axis='x', labelrotation = 90, labelsize=6)
        axs2.locator_params(axis='x', nbins=50)
        #Create annotations
        c2=mplcursors.cursor((img1,img2))
        @c2.connect("add")
        def _(sel2):
            sel2.annotation.set_text('{:.1f}dBm'.format(sel2.target[1]))
            sel2.annotation.set(fontsize=8, ha="left")
            sel2.annotation.get_bbox_patch().set(fc="white", alpha=.5)
        
     

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = Window()
    ui.show()
    sys.exit(app.exec_())
