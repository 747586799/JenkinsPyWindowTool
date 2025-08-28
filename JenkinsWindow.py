import wx
import JenkinsTool
import time
import threading
import ParamsSaveTool
import sys
import os

JobStatus_SUCCESS :str = "SUCCESS"
JobStatus_FAILURE :str = "FAILURE"
JobStatus_WAITTING :str = "WAITTING"
JobStatus_RUNNING :str = "RUNNING"
JobStatus_OTHER :str = "OTHER"

class RunningJob():
    def __init__(self, job, state):
        """运行中的任务 state 0还未查到开始,1已查到开始"""
        self.job = job
        self.state = state
        self.checkCount = 0
        self.logOffset = 0
        self.log = ""
    
    def loadLogs(self, build_number):
        chunk, offset, more = Jenkin.get_build_log_chunk(self.job.name, build_number, self.logOffset)
        self.logOffset = offset
        self.log += chunk
        return chunk

class JenkinsJob():
    def __init__(self, name, status, itemIndex):
        """任务"""
        self.name = name
        self.status = status
        self.itemIndex = itemIndex

class LogPanel(wx.Panel):
    """公共日志面板"""
    def __init__(self, parent):
        super().__init__(parent)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.log_output = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        vbox.Add(self.log_output, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(vbox)

    def append(self, msg):
        self.log_output.AppendText("----------------------------------" + "\n")
        self.log_output.AppendText(msg + "\n")

    def clearLog(self):
        self.log_output.SetValue("")

class LoginPanel(wx.Panel):
    def __init__(self, parent, on_login_success, log_func):
        super().__init__(parent)
        self.isInLogin = False
        self.on_login_success = on_login_success
        self.log = log_func

        vbox = wx.BoxSizer(wx.VERTICAL)

        self.url_input = wx.TextCtrl(self,value="http://192.168.1.26:8750/")
        vbox.Add(self.url_input, 0, wx.EXPAND | wx.ALL, 5)

        self.user_input = wx.TextCtrl(self)
        self.user_input.SetHint("Username")
        self.user_input.SetValue("admin")
        vbox.Add(self.user_input, 0, wx.EXPAND | wx.ALL, 5)

        self.token_input = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.token_input.SetHint("Password / Token")
        self.token_input.SetValue("a12345678")
        vbox.Add(self.token_input, 0, wx.EXPAND | wx.ALL, 5)

        login_btn = wx.Button(self, label="Login")
        login_btn.Bind(wx.EVT_BUTTON, self.login)
        vbox.Add(login_btn, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(vbox)

    def login(self, event):
        if  self.isInLogin == True:
            self.log(f"IsInLogin!! Try again later!")
            return
        self.isInLogin = True
        url = self.url_input.GetValue()
        user = self.user_input.GetValue()
        token = self.token_input.GetValue()

        if not url or not user or not token:
            self.log("Please input all fields.")
            return

        try:
            self.isInLogin = True
            Jenkin.connect(url,user,token)
            user_info = Jenkin.server.get_whoami()
            self.log(f"Connected to Jenkins success as {user_info['fullName']}")
            wx.CallLater(500, lambda: self.on_login_success(Jenkin.server, user_info))
        except Exception as e:
            self.isInLogin = False
            self.log(f"Login failed: {e}")


class MainPanel(wx.Panel):
    def __init__(self, parent, server, user_info, log_func):
        super().__init__(parent)
        self.server = server
        self.log = log_func
        self.initStatus = False
        self.param_controls = {}

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.job_Panel = wx.Panel(self)
        self.job_Panel.SetMinSize((330, -1))
        self.job_sizer = wx.BoxSizer(wx.VERTICAL)
        self.job_Panel.SetSizer(self.job_sizer)
        label = wx.StaticText(self.job_Panel, label=f"Welcome, {user_info['fullName']}! Jenkins connected.")
        self.job_sizer.Add(label, 0, wx.ALL, 10)
         # 左侧：任务列表
        self.job_list = wx.ListCtrl(self.job_Panel, style= wx.LC_REPORT)
        self.image_list = wx.ImageList(32, 32, True)
        addImageToList(self.image_list, JobStatus_SUCCESS)
        addImageToList(self.image_list, JobStatus_FAILURE)
        addImageToList(self.image_list, JobStatus_RUNNING)
        addImageToList(self.image_list, JobStatus_WAITTING)
        addImageToList(self.image_list, JobStatus_OTHER)
        self.job_list.AssignImageList(self.image_list, wx.IMAGE_LIST_SMALL)
        self.job_sizer.Add(self.job_list, 1, wx.EXPAND | wx.ALL, 5)
        hbox.Add(self.job_Panel, 1, flag=wx.EXPAND | wx.ALL, border=5)

        # 右侧：参数区域
        self.param_panel = wx.ScrolledWindow(self, style=wx.VSCROLL)
        self.param_panel.SetScrollRate(5, 5)
        self.param_main_sizer = wx.BoxSizer(wx.VERTICAL)

        #版本参数区域
        box1 = wx.StaticBox(self.param_panel, label="版本参数")
        # box1.SetMinSize(size=(500, -1))
        self.verison_param_sizer = wx.StaticBoxSizer(box1, wx.VERTICAL)
        self.param_main_sizer.Add(self.verison_param_sizer, 0, flag=wx.EXPAND | wx.ALL, border=5)

        #新增版本参数
        h = wx.BoxSizer(wx.HORIZONTAL)
        self.verison_param_sizer.Add(h, 0, flag=wx.EXPAND | wx.ALL, border=5)
        self.addKeyTextCtrl = wx.TextCtrl(self.param_panel)
        self.addKeyTextCtrl.SetMinSize(size=(100, -1))
        h.Add(self.addKeyTextCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        btn = wx.Button(self.param_panel, label="新增版本参数")
        btn.SetMinSize(size=(100, -1))
        btn.Bind(wx.EVT_BUTTON, self.addNewVersionParams)
        h.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        #选择版本参数与读取版本参数
        h = wx.BoxSizer(wx.HORIZONTAL)
        self.verison_param_sizer.Add(h, 0, flag=wx.EXPAND | wx.ALL, border=5)
        self.version_params_choose = wx.Choice(self.param_panel, choices=ParamsTool.getAllKeys())
        self.version_params_choose.SetMinSize(size=(100, -1))
        self.version_params_choose.Bind(wx.EVT_CHOICE, self.on_choice_change)
        h.Add(self.version_params_choose, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        btn = wx.Button(self.param_panel, label="读取版本参数")
        btn.SetMinSize(size=(100, -1))
        btn.Bind(wx.EVT_BUTTON, self.readVersionParams)
        h.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        btn = wx.Button(self.param_panel, label="删除版本参数")
        btn.SetMinSize(size=(100, -1))
        btn.Bind(wx.EVT_BUTTON, self.deleVersionParams)
        h.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.verison_param_lable = wx.StaticText(self.param_panel, label=f"")
        self.verison_param_lable.SetForegroundColour(wx.Colour(99, 130, 173))
        self.verison_param_sizer.Add(self.verison_param_lable, 0, wx.ALL, 10)

        #参数列表区域
        box2 = wx.StaticBox(self.param_panel, label="参数列表")
        # box2.SetMinSize(size=(500, -1))
        self.param_sizer = wx.StaticBoxSizer(box2, wx.VERTICAL)# wx.BoxSizer(wx.VERTICAL)
        self.param_panel.SetSizer(self.param_main_sizer)
        self.param_main_sizer.Add(self.param_sizer, 0, flag=wx.EXPAND | wx.ALL, border=5)
        hbox.Add(self.param_panel, proportion=2, flag=wx.EXPAND | wx.ALL, border=5)

        self.SetSizer(hbox)
        # 加载任务列表
        self.loadJobs()
        # 绑定事件：点击任务
        self.job_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_job_select)

        # 任务执行日志
        self.runnigLogPanel = LogPanel(self)
        hbox.Add(self.runnigLogPanel, 1, flag=wx.EXPAND | wx.ALL, border=5)

    #新增新的版本参数
    def addNewVersionParams(self, event):
        key = self.addKeyTextCtrl.GetValue()
        if key is None or key == "":
            return
        
        versionName = ""
        versionNum = ""
        resourceVersionNum = ""
        branchName = ""
        
        if ParamsSaveTool.VersionName in self.param_controls:
            ctrl = self.param_controls[ParamsSaveTool.VersionName]
            versionName = ctrl.GetValue() if not isinstance(ctrl, wx.Choice) else ctrl.GetStringSelection()
        if ParamsSaveTool.VersionNum in self.param_controls:
            ctrl = self.param_controls[ParamsSaveTool.VersionNum]
            versionNum = ctrl.GetValue() if not isinstance(ctrl, wx.Choice) else ctrl.GetStringSelection()
        if ParamsSaveTool.ResourceVersionNum in self.param_controls:
            ctrl = self.param_controls[ParamsSaveTool.ResourceVersionNum]
            resourceVersionNum = ctrl.GetValue() if not isinstance(ctrl, wx.Choice) else ctrl.GetStringSelection()
        if ParamsSaveTool.BranchName in self.param_controls:
            ctrl = self.param_controls[ParamsSaveTool.BranchName]
            branchName = ctrl.GetValue() if not isinstance(ctrl, wx.Choice) else ctrl.GetStringSelection()
        isNew = ParamsTool.save(key, versionName, versionNum, resourceVersionNum, branchName)
        if isNew == True:
            self.version_params_choose.Append(key)

    #读取版本参数到选中的任务
    def readVersionParams(self, event):
        key = self.version_params_choose.GetStringSelection()
        param : ParamsSaveTool.ParamsSaveData = ParamsTool.get(key)
        if param is not None:
            for key,value in param.Param.items():
                if key in self.param_controls:
                    self.setValueToControls(self.param_controls[key], value)
    
    #删除版本参数
    def deleVersionParams(self, event):
        key = self.version_params_choose.GetStringSelection()
        index = self.version_params_choose.GetSelection()
        self.version_params_choose.Delete(index)
        ParamsTool.dele(key)
        self.version_params_choose.Refresh()  # 刷新控件
        self.version_params_choose.Update()   # 强制重绘
        self.set_verison_param_lable("")

    def on_choice_change(self, event):
        key = self.version_params_choose.GetStringSelection()
        param : ParamsSaveTool.ParamsSaveData = ParamsTool.get(key)
        self.set_verison_param_lable(param.getString())
    
    def set_verison_param_lable(self, value):
        self.verison_param_lable.SetLabel(value)
        self.verison_param_lable.Wrap(480)
        self.verison_param_lable.GetParent().Layout()

    #加载所有任务
    def loadJobs(self):
        jobs = self.server.get_jobs()
        self.job_list.InsertColumn(0, "状态", width=40)
        self.job_list.InsertColumn(1, "任务名", width=200)
        self.job_datas = []
        for i, job in enumerate(jobs):
            data = JenkinsJob(job['name'], "Loading", i)
            self.job_datas.append(data)
        
        for i, item in enumerate(self.job_datas):
            index = self.job_list.InsertItem(i, "", status_image[JobStatus_OTHER])
            self.job_list.SetItem(index, 1, item.name)
        
        # 开启后台线程增量获取
        threading.Thread(target=self.update_jobs_incrementally, daemon=True).start()
        threading.Thread(target=self.checkRunnigJob, daemon=True).start()
    
    #修改任务状态
    def setJobStates(self, index, job):
        status = job.status
        # self.job_list.SetItem(index, 1, status)
        if status in status_image:
            self.job_list.SetItemImage(index, status_image[status])
        else:
            self.job_list.SetItemImage(index, status_image[JobStatus_OTHER])

    #初始时获取所有任务的状态
    def update_jobs_incrementally(self):
        for i, job in enumerate(self.job_datas):
            try:
                time.sleep(0.05)  # 模拟网络延迟
                last_build,last_buildNum = Jenkin.get_last_build_info(job.name)
                if last_build:
                    if last_build['building'] == True:
                        job.status = JobStatus_RUNNING
                        run = RunningJob(job, 0)
                        runningJobCatch[job.name] = run
                    else:
                        job.status = last_build['result']      # SUCCESS / FAILURE / None(执行中)
                    
                if job.status is None:
                    job.status = "None"
                self.log(f"Get Job {job.name} status: {job.status}")
                # self.log(str(last_build))
                # 更新 UI
                wx.CallAfter(self.setJobStates, i, job)
            except BaseException as e:
                import traceback
                traceback.print_exc()
                self.log(f"Get Job State: {job.name} {e}")
        self.initStatus = True
        self.log("Get all job state complete!!")
    
    #获取运行中的任务的状态
    def checkRunnigJob(self):
        while True:
            if self.initStatus:
                needRemove = []
                for jobName, runningJob in runningJobCatch.items():
                    last_build,last_buildNum = Jenkin.get_last_build_info(jobName)
                    if last_build:
                        if last_build['building'] == True:
                            runningJob.job.status = JobStatus_RUNNING
                            runningJob.state = 1
                            self.checkLogRunningLog(runningJob=runningJob,last_buildNum=last_buildNum)
                            wx.CallAfter(self.setJobStates, runningJob.job.itemIndex, runningJob.job)
                            continue
                        elif runningJob.state == 1:
                            runningJob.job.status = last_build['result']
                            wx.CallAfter(self.setJobStates, runningJob.job.itemIndex, runningJob.job)
                            needRemove.append(jobName)
                            self.checkLogRunningLog(runningJob=runningJob,last_buildNum=last_buildNum)
                            self.on_job_buildComplete(runningJob=runningJob)
                            continue

                    if runningJob.state == 0 and runningJob.checkCount >= 10:
                        needRemove.append(jobName)
                    else:
                        runningJob.job.status = JobStatus_WAITTING
                        runningJob.checkCount += 1
                        wx.CallAfter(self.setJobStates, runningJob.job.itemIndex, runningJob.job)
                
                for jobName in needRemove:
                    runningJobCatch.pop(jobName)

            time.sleep(1)  # 避免CPU空转
    
    #判断是否输出任务执行日志
    def checkLogRunningLog(self, runningJob, last_buildNum):
        index = self.job_list.GetFirstSelected()
        if index != -1:
            job_name = self.job_list.GetItemText(index, 1)
            if(runningJob.job.name == job_name):
                log = runningJob.loadLogs(last_buildNum)
                if log != "":
                    self.runnigLogPanel.append(log)
    
    def on_job_buildComplete(self, runningJob):
        self.log(f"任务{runningJob.job.name}执行完成")
        index = self.job_list.GetFirstSelected()
        if index != -1:
            job_name = self.job_list.GetItemText(index, 1)
            if(runningJob.job.name == job_name):
                if self.param_panel.IsEnabled() == False:
                    self.param_panel.Enable(True)

    def on_job_select(self, event):
        index = event.GetIndex()
        job_name = self.job_list.GetItemText(index, 1)
        self.param_sizer.Clear(True)

        h = wx.BoxSizer(wx.HORIZONTAL)
        self.param_sizer.Add(h)

        btn = wx.Button(self.param_panel, label="执行任务")
        btn.Bind(wx.EVT_BUTTON, lambda e, j=index: self.build_job(j))
        h.Add(btn, flag=wx.TOP, border=10)

        btn = wx.Button(self.param_panel, label="读取上次的参数")
        btn.Bind(wx.EVT_BUTTON, lambda e, j=index: self.loadLastParam(j))
        h.Add(btn, flag=wx.TOP, border=10)

        params = self.get_job_parameters(job_name)
        self.param_controls = {}
        for p in params:
            label = wx.StaticText(self.param_panel, label=p['name'])
            self.param_sizer.Add(label, flag=wx.TOP, border=5)
            if p['description'] is not None:
                label = wx.StaticText(self.param_panel, label=p['description'])
                label.SetForegroundColour(wx.Colour(99, 130, 173))
                self.param_sizer.Add(label, flag=wx.TOP, border=5)
            if p['type'].endswith("ChoiceParameterDefinition") and 'choices' in p:
                ctrl = wx.Choice(self.param_panel, choices=p['choices'])
                ctrl.Bind(wx.EVT_MOUSEWHEEL, self.on_mousewheel)
                if p['default'] in p['choices']:
                    ctrl.SetSelection(p['choices'].index(p['default']))
            else:
                ctrl = wx.TextCtrl(self.param_panel)
                if p['default']:
                    ctrl.SetValue(str(p['default']))
            self.param_controls[p['name']] = ctrl
            self.param_sizer.Add(ctrl, flag=wx.EXPAND)

        # 更新滚动区域大小
        self.param_panel.Layout()
        self.param_panel.FitInside()      # 根据子控件大小更新内部滚动区域
        self.param_panel.SetScrollPos(wx.VERTICAL, 0)  # 滚动到顶部

        key = ParamsTool.getKeyByJobName(job_name)
        if key is not None:
            keyindex = self.version_params_choose.FindString(key)
            self.version_params_choose.SetSelection(keyindex)

        self.log(f"选中任务 : {job_name}, 版本参数类型：{key}")

        #加载上次build的参数
        self.loadLastParam(index)
        if job_name in runningJobCatch:
            self.param_panel.Enable(False)
        else:
            self.param_panel.Enable(True)

        if job_name in runningJobCatch:
            self.runnigLogPanel.clearLog()
            self.runnigLogPanel.append(runningJobCatch[job_name].log)

    def on_mousewheel(self, event):
        # 不调用 event.Skip()，阻止默认滚轮行为
        pass

    #读取上次执行任务时的参数
    def loadLastParam(self, jobIndex):
        if self.initStatus == False:
            wx.MessageBox(f"初始化未完成，稍等再开始！", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        job = self.job_datas[jobIndex]
        job_name = job.name
        last_build, last_buildNum = Jenkin.get_last_build_info(job_name)
        buldParams = ""
        if last_build:
            actions = last_build["actions"]
            for action in actions:
                if action.get("_class") == "hudson.model.ParametersAction":
                    for param in action.get("parameters", []):
                        if param["name"] in self.param_controls:
                            self.setValueToControls(self.param_controls[param["name"]], param["value"])
                            buldParams+= f"\n{param["name"]}:{param["value"]}  "
            self.log(f"上次执行任务的参数：{buldParams}")

    #设置控件的值
    def setValueToControls(self, control, value):
        if isinstance(control, wx.TextCtrl):
            control.SetValue(str(value))
        elif isinstance(control, wx.Choice):
            index = control.FindString(str(value))
            control.SetSelection(index)
        else:
            self.log(f"未支持的控件 {str(control)}")

    def get_job_parameters(self, job_name):
        job_info = self.server.get_job_info(job_name)
        parameters = []
        for prop in job_info.get('property', []):
            if 'parameterDefinitions' in prop:
                for p in prop['parameterDefinitions']:
                    param = {
                        "name": p.get('name'),
                        "type": p.get('_class'),
                        "default": p.get('defaultParameterValue', {}).get('value'),
                        "description": p.get('description')
                    }
                    # 如果是 Choice 参数，添加 choices
                    if param['type'].endswith("ChoiceParameterDefinition"):
                        param['choices'] = p.get('choices', [])
                    parameters.append(param)
        return parameters

    #执行任务
    def build_job(self, jobIndex):
        if self.initStatus == False:
            wx.MessageBox(f"初始化未完成，稍等再开始！", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        version_params_key = self.version_params_choose.GetStringSelection()
        if version_params_key is None or version_params_key == "":
            wx.MessageBox(f"请先选择版本参数", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        job = self.job_datas[jobIndex]
        job_name = job.name
        params = {name: ctrl.GetValue() if not isinstance(ctrl, wx.Choice) else ctrl.GetStringSelection()
                  for name, ctrl in self.param_controls.items()}
        result = wx.MessageBox(f"是否确定开始任务{job_name}\n 参数：\n{str(params)}", "提示", wx.YES_NO | wx.ICON_INFORMATION)

        if result == wx.YES:
            queue_id = self.server.build_job(job_name, parameters=params)
            runningJobCatch[job_name] = RunningJob(job, 0)
            job.status = JobStatus_WAITTING
            self.setJobStates(jobIndex, job)
            ParamsTool.saveAndConnect(job_name, version_params_key, params[ParamsSaveTool.VersionName], params[ParamsSaveTool.VersionNum], 
                            params[ParamsSaveTool.ResourceVersionNum], params[ParamsSaveTool.BranchName])
            self.log(f"开始任务 {job_name}, 队列id：{queue_id}")
            self.log(f"参数：\n{str(params)}")
            self.param_panel.Enable(False)

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Jenkins Tool", size=(600, 500))

        self.panel_sizer = wx.BoxSizer(wx.VERTICAL)

        # 顶部动态业务区（LoginPanel / MainPanel）
        self.current_panel = LoginPanel(self, self.show_main_panel, self.log)
        self.panel_sizer.Add(self.current_panel, 2, wx.EXPAND)

        # 底部公共日志区
        self.log_panel = LogPanel(self)
        self.panel_sizer.Add(self.log_panel, 1, wx.EXPAND)

        self.SetSizer(self.panel_sizer)
        self.Centre()
        self.Show()

    def log(self, msg):
        """公共日志方法"""
        self.log_panel.append(msg)

    def show_main_panel(self, server, user_info):
        self.current_panel.Destroy()
        ParamsTool.load()
        self.current_panel = MainPanel(self, server, user_info, self.log)
        self.panel_sizer.Insert(0, self.current_panel, 2, wx.EXPAND)
        self.Maximize(True)
        self.Layout()

Jenkin = JenkinsTool.JenkinsTool()
ParamsTool = ParamsSaveTool.ParamsSaveTool()
status_color = {
    "SUCCESS": wx.Colour(200,255,200),
    "FAILURE": wx.Colour(255,200,200),
    "RUNNING": wx.Colour(255,255,150)
}
runningJobCatch = {
}

status_image = {}
def addImageToList(image_list, imageName):
    img = wx.Image(resource_path(f"Image/{imageName}.png"), wx.BITMAP_TYPE_PNG)
    img = img.Scale(32, 32, wx.IMAGE_QUALITY_HIGH)
    bmp = img.ConvertToBitmap()
    index = image_list.Add(bmp)
    status_image[imageName] = index

def resource_path(relative_path):
    """获取 exe 或脚本运行时的资源路径"""
    if getattr(sys, 'frozen', False):
        # 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

#pyinstaller --onefile --add-data "Image;Image" --clean JenkinsWindow.py
if __name__ == "__main__":
    app = wx.App()
    MainFrame()
    app.MainLoop()