import pandas as pd
import traceback
import tkinter as tk
import tkinter.messagebox
import tkinter.filedialog
import pathlib

allowed_files = [("CSV files","*.csv")]

IMPORT_HEADINGS = ('Operator ID', 'Operator Business Name', 'HCA Miles', '% Total Onshore Miles', 'Baseline Miles Completed in Year', 'Reassessment Miles Completed in Year', 'Total Assessments Completed in Year', 'HCA Immediate Repairs', 'HCA Scheduled Repairs', 'HCA Pressure Test Failure Repairs', 'Total HCA Repairs', 'State Name', 'Pdf Link')
EXPORT_HEADINGS = ('Operator ID', 'Operator Business Name', 'Pipeline Miles', 'HCA Miles', 'Total Assessments Completed in Year', 'Total HCA Repairs')

HEADINGS_ERROR = ('Unexpected headings in {} . Expected:\n'
                  '{}\n'
                  'Do you wish to remove this file from the analysis and retry?')

class HeadingException(Exception):
    pass

class PipeData:
    def __init__(self, pipe_file: pathlib.Path):
        self.df = pd.read_csv(pipe_file, quotechar='"')
        self.active_file = pipe_file

    def check_headings(self):
        df_headings = self.df.columns.tolist()
        try:
            assert len(df_headings) == len(IMPORT_HEADINGS)
            for i in df_headings:
                assert i in IMPORT_HEADINGS
        except AssertionError:
            active_file = str(self.active_file)
            headings_bullets = ''.join([' - ' + i + '\n' for i in IMPORT_HEADINGS])
            raise HeadingException(HEADINGS_ERROR.format(active_file, headings_bullets)) #from None

    def sort_by_id(self):
        a = self.df.sort_values(['Operator ID'], inplace=False)
        return a.reset_index(drop=True)

class DataGroup:
    def __init__(self, df_group: tuple):
        self.id = df_group[0]
        self.df = df_group[1]
        self.business_name = df_group[1].loc[:, 'Operator Business Name'].iloc[0]
    
    def sum_values(self, col):
        return self.df.loc[:, col].sum()
    
    def calc_pipeline_miles(self):
        hcas = self.df.loc[:, 'HCA Miles']
        percent_onshores = self.df.loc[:, '% Total Onshore Miles']
        miles = hcas.divide(percent_onshores.divide(100))
        #return sum_hca/(sum_percent_onshore/100)
        return miles.sum()
    
class SortedData:
    def __init__(self, data: pd.core.frame.DataFrame):
        self.data = data
    
    def group_by_id(self):
        return self.data.groupby(['Operator ID'])

class Groups:
    def __init__(self, groups:pd.core.groupby.generic.DataFrameGroupBy):
        self.groups = groups
        self.processed_data = pd.DataFrame([['']*len(EXPORT_HEADINGS)]*len(groups), columns=EXPORT_HEADINGS)
    
    def populate(self):
        for index, df_group in enumerate(self.groups):
            group = DataGroup(df_group)
            self.processed_data.loc[index, 'Operator ID'] = group.id
            self.processed_data.loc[index, 'Operator Business Name'] = group.business_name
            self.processed_data.loc[index, 'Pipeline Miles'] = group.calc_pipeline_miles()
            self.processed_data.loc[index, 'HCA Miles'] = group.sum_values('HCA Miles')
            self.processed_data.loc[index, 'Total Assessments Completed in Year'] = group.sum_values('Total Assessments Completed in Year')
            self.processed_data.loc[index, 'Total HCA Repairs'] = group.sum_values('Total HCA Repairs')

class FileHandler:
    def __init__(self, master):
        self.files = []
        self.master = master
        self.active_file = None
        self.save_folder = None

    def add_files(self):
        tk_in = tk.filedialog.askopenfilenames(parent=self.master, filetypes=allowed_files)
        self.files += [pathlib.Path(i) for i in tk_in]
    
    def ask_out(self):
        last_file = pathlib.Path(self.files[-1])
        last_folder = last_file.parent
        self.save_folder = tk.filedialog.askdirectory(parent=self.master, title='Choose output folder', initialdir=last_folder)
    
    
    def looper(self, loop_file, loop_out_file):
        data = PipeData(loop_file)
        self.active_file = data.active_file
        data.check_headings()

        sorted_data = SortedData(data.sort_by_id())
        groups = Groups(sorted_data.group_by_id())
        groups.populate()
        groups.processed_data.to_csv(loop_out_file, index=False)
    
    def runner(self):
        self.ask_out()
        for i in self.files:
            in_path = pathlib.Path(i)
            save_fpath = pathlib.Path(self.save_folder)
            out_path = save_fpath.joinpath(in_path.stem + '_processed.csv')
            self.looper(in_path, out_path)
        tk.messagebox.showinfo(title='Completed', message='Calculations completed')
        self.clear_files()
    
    def clear_files(self):
        self.files = []
        tk.messagebox.showinfo(title='Flies cleared', message='Files cleared')
    
    def remove_problem(self, problem: str):
        self.files.remove(problem)

class App:
    def __init__(self, master):
        master.report_callback_exception = self.report
        self.file_handler = FileHandler(master)
        self.make_GUI(master)
    
    def report(self, *args):
        err = traceback.format_exception(*args)
        if 'HeadingException' in err[-1]: #TODO use isinstance to check? not sure what to check
            response = tk.messagebox.askyesnocancel(title='Do you wish to continue', message=args[1])
            if response == True:
                self.file_handler.remove_problem(self.file_handler.active_file)
                self.file_handler.runner()
        else:
            tk.messagebox.showerror(title='Error', message=args[1])
        
    def make_GUI(self, master):
        master.title('Pipe csv processor')
        master.geometry('300x100')
        self.frame = tk.Frame(master)
        self.frame.grid(row=0, column=0)
        self.add_files_button = tk.Button(self.frame, text='Add files', command=self.file_handler.add_files)
        self.add_files_button.grid(row=0, column=0)
        self.run_button = tk.Button(self.frame, text='Process', command=self.file_handler.runner)
        self.run_button.grid(row=0, column=1)
        self.clear_button = tk.Button(self.frame, text='Clear', command=self.file_handler.clear_files)
        self.clear_button.grid(row=0, column=2)
        
root = tk.Tk()
app = App(root)
root.mainloop()

