# Render 배포 빠른 가이드

## 1. GitHub에 최신 파일 반영
`publish_to_github.bat`을 실행합니다.

GitHub 저장소:
https://github.com/hijaewook/songlim

## 2. 배포 파일 확인
`check_deploy_files.bat` 실행

아래 파일이 모두 OK여야 합니다.
- app.py
- requirements.txt
- Dockerfile
- render.yaml
- static/index.html

## 3. Render 배포
`deploy_to_render.bat` 실행

브라우저가 Render 배포 페이지를 엽니다.

최초 한 번:
1. Render 로그인
2. GitHub 연결/승인
3. `hijaewook/songlim` 저장소 확인
4. Blueprint 내용 확인
5. Deploy Blueprint 또는 Apply 클릭

배포가 끝나면 Render가 `https://...onrender.com` 형태의 공개 URL을 제공합니다.

## 4. 친구에게 공유
친구는 위 HTTPS 주소만 브라우저에서 열면 됩니다.

게임 클라이언트는 페이지가 HTTPS이면 자동으로 `wss://` WebSocket을 사용합니다.

## 5. 이후 업데이트
코드를 수정한 뒤 `publish_to_github.bat`만 다시 실행하면 됩니다.

`render.yaml`에는 `autoDeployTrigger: commit`이 설정되어 있으므로 Render가 GitHub의 새 커밋을 감지해 자동 배포합니다.

## 무료 플랜 참고
Render Free 웹 서비스는 장시간 사용하지 않으면 sleep 상태가 될 수 있습니다.
그 뒤 첫 접속은 서버가 다시 깨어나느라 시간이 걸릴 수 있습니다.
