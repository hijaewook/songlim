# 2인 협동 로그라이크 프로토타입

## 포함 내용
- 캐릭터 2명
  - 이재욱: 남성 / 근거리 / 패링형
  - 김우찬: 여성 / 원거리 / 표식·사격형
- 5개 스테이지
- 1~3 스테이지 클리어 시 스킬 1개씩 해금
- 스테이지 종료 후 보상 3택
- 5스테이지 보스: 심연 기사 바르칸
- WebSocket 기반 2인 실시간 협동
- 서버 권위형에 가까운 전투 판정
- 사람 형태의 간단한 Canvas 캐릭터 렌더링

## 실행 방법 - Windows
1. Python 3.10 이상 설치
2. `run.bat` 더블클릭
3. 브라우저에서 http://127.0.0.1:8000 접속
4. 두 명 테스트 시 브라우저 창을 두 개 열고 같은 방 코드 사용

## 실행 방법 - macOS / Linux
터미널에서:

```bash
chmod +x run.sh
./run.sh
```

그 다음 브라우저에서 http://127.0.0.1:8000 접속

## 조작
- WASD: 이동
- 마우스: 조준
- 좌클릭: 일반 공격
- Q / E / R: 스킬 1 / 2 / 3
- Space: 회피

## 스킬
### 이재욱
- Q 강철 반격: 짧은 패링. 성공 시 공격 무효화 + 다음 공격 강화
- E 돌진 베기: 전방 돌진 + 피해 + 취약 디버프
- R 수호의 원: 주변 아군 피해 감소

### 김우찬
- Q 추적 표식: 가까운 적에게 표식, 받는 피해 증가
- E 분열 사격: 3방향 탄환
- R 유성 저격: 강한 관통탄, 표식 대상 적중 시 범위 폭발

## 참고
이 빌드는 게임성 검증용 MVP입니다. 그래픽/애니메이션/정밀 충돌/매치메이킹/DB 저장은 의도적으로 최소화했습니다.


---

# GitHub 자동 업로드

Windows에서 `publish_to_github.bat`을 더블클릭하세요.

이 스크립트는 다음을 자동으로 수행합니다.

1. Git이 없으면 `winget`으로 Git 설치
2. GitHub CLI(`gh`)가 없으면 자동 설치
3. GitHub 로그인이 안 되어 있으면 브라우저 로그인 실행
4. 저장소 이름 입력
5. Public / Private 선택
6. Git 초기화, commit, GitHub 저장소 생성, push

처음 실행은 GitHub 계정 승인을 위해 브라우저 로그인 과정이 한 번 필요합니다.
이후에는 같은 BAT을 다시 실행하면 변경 파일을 commit/push할 수 있습니다.

`winget`이 없는 Windows라면 Microsoft Store에서 **App Installer**를 설치해야 합니다.

# Docker 배포

프로젝트 루트에 `Dockerfile`이 포함되어 있습니다.

Docker Desktop이 설치되어 있다면 `test_docker.bat`으로 로컬 컨테이너 실행을 시험할 수 있습니다.

직접 명령어로 확인하려면:

```bash
docker build -t coop-roguelike .
docker run --rm -p 8000:8000 coop-roguelike
```

그 뒤 브라우저에서:

```text
http://127.0.0.1:8000
```

# Render 같은 Docker 호스팅에 배포

`render.yaml`도 포함되어 있습니다. GitHub에 push한 뒤 Render에서 해당 저장소를 연결해 Blueprint 또는 Docker Web Service로 배포할 수 있습니다.

배포 후에는 Render가 제공한 HTTPS 주소로 접속하면 됩니다. 현재 게임 클라이언트는 접속한 페이지의 주소를 기준으로 WebSocket 주소를 자동 생성하므로 HTTPS 환경에서는 자동으로 WSS를 사용합니다.

# 파일 설명

- `run.bat` : 내 PC에서만 로컬 실행
- `run_network.bat` : 같은 LAN에서 테스트할 수 있도록 0.0.0.0:8000으로 실행
- `publish_to_github.bat` : Git/GitHub CLI 설치 + GitHub 저장소 생성/업로드
- `test_docker.bat` : Docker 로컬 빌드/실행
- `Dockerfile` : 클라우드 배포용 컨테이너 정의
- `render.yaml` : Render 배포용 Blueprint
