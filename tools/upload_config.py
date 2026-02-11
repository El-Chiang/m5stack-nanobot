# 通过 REPL 将 config.py 写入设备文件系统
f = open("config.py", "w")
f.write('WIFI_SSID = "1002"\n')
f.write('WIFI_PASSWORD = "10000002"\n')
f.write('RELAY_SERVER = "http://192.168.31.84:8080"\n')
f.write('AUDIO_SAMPLE_RATE = 16000\n')
f.write('AUDIO_BIT_DEPTH = 8\n')
f.close()
print("config.py written OK")
