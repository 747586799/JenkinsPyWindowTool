import sys
from pathlib import Path
import json
import os

VersionName = "VersionName"
VersionNum = "VersionNum"
ResourceVersionNum = "ResourceVersionNum"
BranchName = "BranchName"

class ParamsSaveData():
    def __init__(self, key, versionName, versionNum, resourceVersionNum, branchName):
        self.key = key
        self.Param = {VersionName:versionName, VersionNum: versionNum, ResourceVersionNum: resourceVersionNum, BranchName:branchName}

    def refreshData(self, versionName, versionNum, resourceVersionNum, branchName):
        self.Param = {VersionName:versionName, VersionNum: versionNum, ResourceVersionNum: resourceVersionNum, BranchName:branchName}

    def getString(self):
        return str(self.Param)

class ParamsSaveTool():
    def __init__(self):
        self.Params = {}
        self.JobConnect = {}
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys._MEIPASS)
        else:
            base_dir = Path(__file__).resolve().parent

        # 假设要在当前目录的 output 文件夹中生成 result.txt
        if getattr(sys, 'frozen', False):
            # 打包后的 exe
            base_dir = Path(os.path.dirname(sys.executable))
        else:
            # 脚本运行
            base_dir = Path(__file__).resolve().parent

        out_dir = base_dir / 'ParamsSave'
        out_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = out_dir / 'ParamsSave.txt'

    def getAllKeys(self):
        keys = []
        for key in self.Params.keys():
            keys.append(key)
        return keys
    
    def load(self):
        if self.file_path.exists():
            json_str = self.file_path.read_text(encoding='utf-8')
            fianlData = json.loads(json_str)
            for data in fianlData["Params"]:
                p = ParamsSaveData(data["key"], data["Param"][VersionName], data["Param"][VersionNum], data["Param"][ResourceVersionNum], data["Param"][BranchName])
                self.Params[p.key] = p
            self.JobConnect = fianlData["JobConnect"]

    def get(self, key):
        if key in self.Params:
            return self.Params[key]
        
    def getKeyByJobName(self, jobName):
        if jobName in self.JobConnect:
            if self.JobConnect[jobName] in self.Params:
                return self.JobConnect[jobName]
        
    def dele(self, key):
        if key in self.Params:
            self.Params.pop(key)
            self.saveAll()
    
    def saveAndConnect(self, jobName, key, versionName, versionNum, resourceVersionNum, branchName):
        self.JobConnect[jobName] = key
        return self.save(key=key,versionName=versionName,versionNum=versionNum,resourceVersionNum=resourceVersionNum,branchName=branchName)
            
    def save(self, key, versionName, versionNum, resourceVersionNum, branchName):
        saveData:ParamsSaveData = None
        isNew = True
        if key in self.Params:
            saveData = self.Params[key]
            saveData.refreshData(versionName, versionNum, resourceVersionNum, branchName)
            isNew = False
        else: 
            saveData = ParamsSaveData(key, versionName, versionNum, resourceVersionNum, branchName)
            self.Params[key] = saveData
        self.saveAll()
        return isNew
    
    def saveAll(self):
        fianlData = {}
        fianlData["Params"] = []
        fianlData["JobConnect"] = self.JobConnect
        for key,data in self.Params.items():
            fianlData["Params"].append(data)
        json_str = json.dumps(fianlData, default=lambda o: o.__dict__)
        self.file_path.write_text(json_str, encoding='utf-8')

if __name__ == "__main__":
    tool = ParamsSaveTool()
    tool.load()