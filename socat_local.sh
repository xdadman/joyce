nohup socat TCP-LISTEN:2000,reuseaddr,fork FILE:/dev/ttyAMA2,b9600,cs8,parenb=0,cstopb=0,raw,echo=0 &

