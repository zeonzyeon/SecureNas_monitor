# PlanB-NAS Raspberry Pi 배포

라즈베리파이에서는 Windows UNC 경로(`\\192.168.0.204\PlanB_Media`)를 직접 쓰지 않고, NAS 공유를 로컬 경로에 마운트한 뒤 앱에서 그 경로를 사용합니다.

## 1. 라즈베리파이 준비

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip cifs-utils tailscale
sudo tailscale up
```

Tailscale 로그인 후 Pi의 Tailscale IP를 확인합니다.

```bash
tailscale ip -4
```

## 2. NAS 공유 마운트

```bash
sudo mkdir -p /mnt/planb_media
sudo mkdir -p /etc/samba/credentials
sudo nano /etc/samba/credentials/planb-nas
```

파일 내용:

```text
username=NAS계정명
password=NAS비밀번호
```

권한 설정:

```bash
sudo chmod 600 /etc/samba/credentials/planb-nas
```

`/etc/fstab`에 추가:

```text
//192.168.0.204/PlanB_Media /mnt/planb_media cifs credentials=/etc/samba/credentials/planb-nas,iocharset=utf8,uid=pi,gid=pi,file_mode=0664,dir_mode=0775,nofail,_netdev 0 0
```

마운트 확인:

```bash
sudo mount -a
ls -la /mnt/planb_media
```

## 3. 앱 설치

```bash
sudo mkdir -p /opt/planb-nas
sudo chown -R pi:pi /opt/planb-nas
cd /opt/planb-nas
```

프로젝트 파일을 `/opt/planb-nas`에 복사한 뒤:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp deploy/raspberry-pi.env.example .env
nano .env
```

`.env`에서 최소한 아래 값을 실제 값으로 바꿉니다.

```text
SECRET_KEY=긴_랜덤_문자열
NAS_MONITOR_PATH=/mnt/planb_media
ADMIN_PASSWORD=관리자_비밀번호
```

## 4. 서비스 등록

```bash
sudo cp deploy/planb-nas.service /etc/systemd/system/planb-nas.service
sudo systemctl daemon-reload
sudo systemctl enable --now planb-nas
sudo systemctl status planb-nas
```

로그 확인:

```bash
journalctl -u planb-nas -f
```

## 5. 접속

같은 Tailscale 계정에 로그인된 기기에서 접속합니다.

```text
http://라즈베리파이_Tailscale_IP:5000
```

예:

```text
http://100.x.y.z:5000
```

Tailscale MagicDNS를 켰다면 기기명으로도 접속할 수 있습니다.

```text
http://raspberrypi:5000
```
