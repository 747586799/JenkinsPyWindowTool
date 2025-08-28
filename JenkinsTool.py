import jenkins
import time
import JenkinsEx
import sys

class JenkinsTool:
    
    def __init__(self):
        self.jobs = {}
        self.viewName = None
        return

    def connect(self, url, username, password, viewName):
        self.server = JenkinsEx.JenkinsEx(url, username=username, password=password)
        self.viewName = viewName

    def get_jobs(self):
        """获取所有任务列表"""
        self.jobs = self.server.get_jobs(view_name=self.viewName)
        return self.jobs
    
    def get_job(self, job_name):
        if job_name in self.jobs:
            return self.jobs[job_name]
        else:
            return

    def build_job(self, job_name, params=None):
        """构建任务（支持参数化构建）"""
        queue_number = self.server.build_job(job_name, parameters=params or {})
        print(f"Job {job_name} 已加入队列: {queue_number}")
        return queue_number

    def get_build_info(self, job_name, build_number):
        """获取构建信息"""
        return self.server.get_build_info(job_name, build_number)
    
    def get_job_info(self, job_name):
        """获取任务信息"""
        return self.server.get_job_info(job_name)
    
    def get_last_build_number(self, job_name):
        """获取最近一次构建号"""
        job_info = self.server.get_job_info(job_name)
        if job_info and job_info['lastBuild']:
            return job_info['lastBuild']['number']
        else:
            return None
    
    def get_last_build_info(self, job_name):
        """获取最近一次构建"""
        lastBuildNum = self.get_last_build_number(job_name)
        if lastBuildNum:
            buildInfo = self.get_build_info(job_name, lastBuildNum)
            return buildInfo,lastBuildNum
        return None,0

    def track_build(self, job_name, build_number, interval=5):
        """轮询方式追踪构建进度"""
        while True:
            try:
                info = self.get_build_info(job_name, build_number)
                if info['building']:
                    est = info.get('estimatedDuration', 0) / 1000
                    elapsed = (time.time() * 1000 - info['timestamp']) / 1000
                    progress = min(int(elapsed / est * 100), 99) if est > 0 else 0
                    print(f"构建中... {progress}%")
                else:
                    print(f"构建完成，结果: {info['result']}")
                    break
            except jenkins.NotFoundException:
                print("等待构建开始...")
            time.sleep(interval)

    def get_running_builds(self):
        """获取所有正在执行的任务"""
        builds = self.server.get_running_builds()
        result = []
        for b in builds:
            result.append({
                "name": b["name"],
                "number": b["number"],
                "url": b["url"]
            })
        return result

    def get_build_log_chunk(self, job_name, build_number, offset=0):
        return self.server.get_build_log_chunk(job_name,build_number,offset)


if __name__ == "__main__":
    jenkins_url = "http://192.168.1.26:8750/"
    username = "admin"
    password = "a12345678"

    tool = JenkinsTool(jenkins_url, username, password)

    # 1. 获取任务
    print("任务列表:", tool.get_jobs())

    # 2. 执行参数化构建
    params = {"TestParams": "main"}
    tool.build_job("PyJobTest", params)
    # time.sleep(10)
    # while True:
    #     result = tool.get_running_builds()
    #     if len(result) <= 0:
    #         break
    #     print(f"正在执行任务 {result}")
    #     time.sleep(1)
    # 3. 获取最后一次构建号并追踪进度
    build_number = tool.get_last_build_number("PyJobTest")
    tool.track_build("PyJobTest", build_number)
