from watchfiles import watch

for changes in watch(r'S:\TA3\xray_cam\Dollar'):
    for c_name,path in changes:
        print(c_name.name)