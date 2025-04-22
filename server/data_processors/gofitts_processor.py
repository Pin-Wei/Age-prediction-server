#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import ast
import numpy as np
import pandas as pd

class GoFittsProcessor:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.id_column = "指定代號"
        self.half_width = 960
        self.half_height = 540
        self.modified_jar_path = os.path.join("GoFitts_modified.jar")  

    def convert_file(self):
        df = pd.read_csv(self.file_path)

        if self.id_column not in df.columns:
            raise ValueError("ID column not found in csv!")
        self.subject_id = df[self.id_column].iloc[0]

        df = df.loc[:, ["sequence_loop.thisN", "trial_loop.thisN", "from", "to", "mouse.x", "mouse.y", "mouse.time", "w", "a"]]
        df.rename(columns={
            "sequence_loop.thisN": "seq",
            "trial_loop.thisN": "trial",
            "mouse.x": "x",
            "mouse.y": "y",
            "mouse.time": "t"
        }, inplace=True)
        df = df.dropna()
        df["w"] = df["w"].astype(int)
        df["a"] = df["a"].astype(int)
        df["seq"] = df["seq"].astype(int)
        df["trial"] = df["trial"].astype(int)
        df["x"] = df["x"].apply(lambda str_arr: [str(int(x + self.half_width)) for x in ast.literal_eval(str_arr)])
        df["y"] = df["y"].apply(lambda str_arr: [str(int(y + self.half_height)) for y in ast.literal_eval(str_arr)])
        df["t"] = df["t"].apply(lambda str_arr: [str(int(sec * 1000)) for sec in ast.literal_eval(str_arr)])

        output_csv_path = os.path.join(
            os.path.dirname(self.file_path), f"GoFitts-{self.subject_id}.sd3"
        )        
        with open(output_csv_path, "w") as f:
            f.write("TRACE DATA\n")
            f.write("App,self.subject_id,Condition,Session,Group,TaskType,SelectionMethod,Block,Sequence,A,W,Trial,from_x,from_y,to_x,to_y,{t_x_y}\n")
            for _, row in df.iterrows():
                from_x, from_y = [round(_, 1) for _ in ast.literal_eval(row["from"])]
                to_x, to_y = [round(_, 1) for _ in ast.literal_eval(row["to"])]
                from_to = ",".join([str(_) for _ in [from_x + self.half_width, from_y + self.half_height, to_x + self.half_width, to_y + self.half_height]])
                for d in ["t", "x", "y"]:
                    f.write(f"FittsTask,{self.subject_id},C00,S00,G00,2D,DT0,B00,{row['seq']},{row['a']},{row['w']},{row['trial']},{from_to},{d}=,{','.join(row[d])}\n")
        
        return output_csv_path
    
    def parse_with_jar(self, output_csv_path):        
        if not os.path.isfile(self.modified_jar_path):
            print("GoFitts_modified.jar not found! You will not be able to convert to csv.")
        else:
            os.system(f"java -jar {self.modified_jar_path} -p {output_csv_path}")
            print("Generated trial and sequence summary!")

    def make_summary(self, seq_summary_path, summary_path):
        df = pd.read_csv(self.file_path)
        seq_df = pd.read_csv(seq_summary_path)
        
        seq_cnt = len(seq_df)        
        leave_time = []
        point_time = []
        throughput = []
        
        for i in range(seq_cnt):
            leave_time.append(df[df["sequence_loop.thisN"] == i]["leave_time"].dropna().mean() * 1000)
            point_time.append(seq_df[seq_df["Sequence"] == i]["PT"].item())
            throughput.append(seq_df[seq_df["Sequence"] == i]["TP"].item())
        
        # calculate slope
        def slope(y):
            x = np.arange(len(y))
            A = np.vstack([x, np.ones(len(x))]).T
            m, _ = np.linalg.lstsq(A, y, rcond=None)[0]
            return m
            
        header = ["ID"]
        for name in ["LeaveTime", "PointTime", "Throughput"]:
            for i in range(seq_cnt):
                header.append(f"GOFITTS_BEH_ID{i}_{name}")
            header.append(f"GOFITTS_BEH_SLOPE_{name}")
        
        data = [self.subject_id]
        for array in [leave_time, point_time, throughput]:
            for i in range(seq_cnt):
                data.append(array[i])
            data.append(slope(array))
            
        with open(summary_path, "w") as file:
            file.write(",".join(header))
            file.write('\n')
            file.write(",".join([str(x) for x in data]))
            file.write('\n')
        
        print("Generated final summary!")    

    def process_subject(self, file_path):
        self.file_path = file_path
        output_csv_path = self.convert_file()
        self.parse_with_jar(output_csv_path)
        seq_summary_path = os.path.join(os.path.dirname(self.file_path), f"GoFitts-{self.subject_id}-sequence-summary.csv")
        summary_path = os.path.join(os.path.dirname(self.file_path), f"GoFitts-{self.subject_id}-summary.csv")
        self.make_summary(seq_summary_path, summary_path)
        df = pd.read_csv(summary_path)
        df = df.rename(columns={'ID': self.id_column})
        
        return df

    



    