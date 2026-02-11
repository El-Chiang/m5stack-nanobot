"""音频播放与麦克风录音封装

音频输出: ESP32 内部 DAC → GPIO 25 (DAC1) → PAM8303 模拟功放
麦克风输入: 模拟 MEMS → ADC GPIO 34
"""

from machine import DAC, Pin, ADC, Timer
import urequests
import config

# 引脚定义
DAC_PIN = 25
MIC_PIN = 34


class AudioPlayer:
    """通过 DAC (GPIO 25) 播放 8-bit unsigned PCM 音频"""

    def __init__(self):
        self._dac = DAC(Pin(DAC_PIN))
        self._playing = False

    def play_raw(self, data, sample_rate=None):
        """播放 RAW PCM 数据（8-bit unsigned）"""
        if sample_rate is None:
            sample_rate = config.AUDIO_SAMPLE_RATE
        self._playing = True
        # 逐样本写入 DAC（基础实现，后续可用 Timer 中断优化节奏）
        interval_us = 1_000_000 // sample_rate
        for i in range(len(data)):
            if not self._playing:
                break
            self._dac.write(data[i])
            # 简单延时控制采样率
            import utime
            utime.sleep_us(interval_us)
        self._dac.write(128)  # 回到中点静音
        self._playing = False

    def play_from_url(self, url):
        """从中继服务下载 WAV/PCM 并播放"""
        try:
            resp = urequests.get(url)
            if resp.status_code == 200:
                self.play_raw(resp.content)
            resp.close()
        except Exception as e:
            print("audio download error:", e)

    def stop(self):
        self._playing = False
        self._dac.write(128)

    @property
    def is_playing(self):
        return self._playing


class Microphone:
    """通过 ADC (GPIO 34) 录制音频"""

    def __init__(self):
        self._adc = ADC(Pin(MIC_PIN))
        self._adc.atten(ADC.ATTN_11DB)  # 满量程 ~3.3V
        self._adc.width(ADC.WIDTH_12BIT)
        self._recording = False
        self._buffer = bytearray()

    def start_recording(self):
        self._buffer = bytearray()
        self._recording = True
        self._record_loop()

    def _record_loop(self):
        """采集循环（阻塞式，在 main.py 中由按键松开中断）"""
        sample_interval_us = 1_000_000 // config.AUDIO_SAMPLE_RATE
        import utime
        while self._recording:
            val = self._adc.read()  # 0-4095 (12-bit)
            # 转换为 8-bit unsigned
            self._buffer.append(val >> 4)
            utime.sleep_us(sample_interval_us)

    def stop_recording(self):
        self._recording = False
        data = bytes(self._buffer)
        self._buffer = bytearray()
        return data

    @property
    def is_recording(self):
        return self._recording
