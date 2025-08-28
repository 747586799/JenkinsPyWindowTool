import jenkins

class JenkinsEx(jenkins.Jenkins):
    def get_build_log_chunk(self, job_name, build_number, offset=0):
        """
        获取一段 Jenkins 构建日志（基于 progressiveText）
        :param job_name: 任务名
        :param build_number: 构建号
        :param offset: 日志起始偏移
        :return: (日志文本, 新的offset, 是否还有更多数据)
        """
        log_url = f"{self.server}/job/{job_name}/{build_number}/logText/progressiveText"
        resp = self._session.get(log_url, params={"start": offset})
        resp.raise_for_status()

        text = resp.text
        new_offset = int(resp.headers.get("X-Text-Size", offset))
        more_data = resp.headers.get("X-More-Data") == "true"

        return text, new_offset, more_data
