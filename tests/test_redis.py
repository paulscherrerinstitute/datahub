import redis

with redis.Redis(host='std-daq-build',port=6379,db=0) as rc:
    rc.set('test:hello','World')
    print(rc.get('test:hello'))