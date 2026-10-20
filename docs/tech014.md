> **쉽게 이해하기**
>
> - **한 줄 요약** — `print` 대신 쓰는 기록 도구입니다. 레벨(DEBUG ~ CRITICAL) 과 출력 대상을 코드 수정 없이 설정으로 바꿉니다.
> - **비유하면** — 자동차 블랙박스. 평소엔 조용하지만 사고(502) 가 나면 스택까지 남아 있습니다.
> - **이 프로젝트에서는** — 모듈마다 `logger = logging.getLogger(__name__)` 를 두고, 외부 DB 실패 시 `logger.exception` 으로 원인을 기록합니다.
> - **기억할 것** — f-string 대신 `logger.info("%s", x)`. 레벨이 꺼져 있으면 문자열을 만들지도 않습니다.

**로깅(`logging` 모듈)** 은 `print()` 와 달리 레벨 · 출력 대상 · 포맷을 설정으로 제어하고, 예외 스택을 함께 남길 수 있습니다. 이 프로젝트는 모듈마다 `logger = logging.getLogger(__name__)` 를 두고, 장애(502) 와 자원 정리 실패를 기록합니다.

---

### 1. 모듈 로거 관용구

```python
import logging
logger = logging.getLogger(__name__)      # "backend.adapters.gateways.lab_redis"
```

* `__name__` 을 쓰면 로거 이름이 **패키지 경로와 같아져** 계층적으로 제어할 수 있습니다.
  `logging.getLogger("backend.adapters").setLevel(logging.DEBUG)` → 하위 모듈 전부 적용.
* 루트 로거(`logging.getLogger()`) 에 직접 쓰지 마세요. 어느 모듈이 남긴 로그인지 알 수 없습니다.

### 2. 레벨

| 레벨 | 용도 | 이 프로젝트 |
|---|---|---|
| `DEBUG` | 개발 중 상세 추적 | Redis JSON 로드 크기, JWT 디코드 실패 사유 |
| `INFO` | 정상 이벤트 | 자원 종료(`closed mongo`) |
| `WARNING` | 비정상이지만 계속 동작 | — |
| `ERROR` | 기능 실패 | 자원 정리 실패 |
| `CRITICAL` | 프로세스 지속 불가 | — |

### 3. `%s` 지연 포매팅 — f-string 을 쓰지 않는 이유

```python
logger.debug("redis load key=%s bytes=%d", key, len(raw))      # 권장
logger.debug(f"redis load key={key} bytes={len(raw)}")         # 비권장
```

* f-string 은 로그 레벨이 꺼져 있어도 **문자열을 먼저 만듭니다**. `%s` 방식은 실제로 출력될 때만 포매팅합니다.
* 구조화 로깅 도구(Sentry 등) 는 메시지 템플릿과 인자를 분리해 **같은 템플릿의 로그를 묶어** 줍니다.

### 4. 예외 스택 남기기 — `logger.exception` / `exc_info`

```python
# backend/infrastructure/clients.py — except 블록 안
except Exception:
    logger.exception("failed to close %s", name)        # ERROR 레벨 + 현재 예외의 트레이스백

# backend/adapters/api/error_handlers.py — except 블록 밖에서 예외 객체를 들고 있을 때
logger.exception("external service failure on %s %s", request.method, request.url.path, exc_info=exc)
```

* `logger.exception()` 은 `logger.error(..., exc_info=True)` 의 축약. **except 블록 안** 에서만 현재 예외를 자동으로 찾습니다.
* 예외 객체를 변수로 들고 있으면 `exc_info=exc` 로 넘깁니다. `raise ... from exc` 로 체이닝된 원인(`__cause__`) 까지 함께 출력됩니다.

### 5. 무엇을 로그에 남기지 않을 것인가

```python
# backend/adapters/security/jwt_token_provider.py
except JWTError as exc:
    logger.debug("jwt decode failed: %s", exc)       # 토큰 원문은 남기지 않음
    return None
```

* 비밀번호 · 토큰 · API 키 · 개인정보는 **DEBUG 레벨에도** 남기지 않습니다. 운영에서 DEBUG 가 켜지는 순간 유출됩니다.
* 클라이언트에게는 실패 사유를 뭉뚱그려(`AuthenticationError` 401) 알리고, 상세 사유는 서버 로그에만 둡니다.

### 6. 설정 — 애플리케이션 진입점에서 한 번

```python
# 예: uvicorn 실행 전 또는 main.py 상단
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
```

* 라이브러리 코드(게이트웨이 · 유스케이스) 는 **설정하지 않고 로거만 얻어** 씁니다. 설정은 앱(또는 uvicorn `--log-config`) 의 책임입니다.
* `dictConfig` 로 핸들러(파일 · 콘솔 · JSON) 와 모듈별 레벨을 한 곳에서 관리할 수 있습니다.

### 7. 테스트에서 로그 끄기 / 검사하기

```python
logging.disable(logging.CRITICAL)                 # 전부 끄기 (E2E 검증 스크립트에서 사용)
def test_x(caplog):                               # pytest 픽스처
    with caplog.at_level(logging.DEBUG):
        ...
    assert "redis load" in caplog.text
```

### 8. `print` 가 허용되는 곳

* 일회성 스크립트, CLI 의 사용자 출력. 서버 코드에서는 `print` 를 쓰지 않습니다 — 레벨도, 출처도, 타임스탬프도 없습니다.

---

이 프로젝트의 규칙: **정상 흐름(404 · 400) 은 로그를 남기지 않고, 장애(502) 와 정리 실패는 스택까지 남긴다.** 404 를 ERROR 로 찍으면 진짜 장애가 노이즈에 묻힙니다. 로그 레벨은 "누가 이 메시지를 봐야 하는가" 에 대한 답입니다.
