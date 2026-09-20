# Standalone HWPX Document Automation

## 한국어

한컴오피스, COM, LibreOffice, 인터넷 연결 없이 한국어 HWPX 문서를 생성하고 검증하는 Codex 스킬입니다. 레거시 바이너리 `.hwp`가 아닌 표준 `.hwpx`를 출력합니다.

주요 기능:

- JSON Document Spec으로 문단, 제목, 표, 이미지, 수식, 각주, 목차와 색인을 구성
- 완전한 HWPX 패키지 생성과 내부 참조·ID·매니페스트 자동 검증
- 공문, 보도자료, 서식, 시험지, 논문, 정책보고서용 선택형 프리셋 제공
- Python 표준 라이브러리만 사용하는 오프라인 실행

기본 흐름은 가볍게 유지합니다. 먼저 문서 구성안을 사용자에게 한 번 확인받고, 템플릿 없는 최소 명세를 작성한 다음 빌드합니다. 프리셋 템플릿은 사용자가 명시적으로 요청한 경우에만 적용합니다.

```powershell
python scripts/hwpx_tool.py build request.json -o result.hwpx
python scripts/hwpx_tool.py validate result.hwpx
python scripts/hwpx_tool.py inspect result.hwpx
```

자세한 입력 형식은 `references/document-spec.md`, 지원 범위는 `references/feature-status.md`를 참고하세요. 스킬 사용 지침은 `SKILL.md`에 있습니다.

## English

A standalone Codex skill for creating and validating Korean HWPX documents without Hancom Office, COM, LibreOffice, or internet access. It produces standard `.hwpx` files rather than legacy binary `.hwp` files.

Key capabilities:

- Build paragraphs, headings, tables, images, equations, notes, TOCs, and indexes from a JSON Document Spec
- Generate complete HWPX packages and validate internal references, IDs, manifests, and package structure
- Provide opt-in presets for official letters, press releases, forms, exams, academic papers, and policy reports
- Run offline using only the Python standard library

The default workflow stays lightweight: present one short document-structure checkpoint, create a minimal untemplated spec after confirmation, and build it. Preset templates are used only when the user explicitly requests one.

```powershell
python scripts/hwpx_tool.py build request.json -o result.hwpx
python scripts/hwpx_tool.py validate result.hwpx
python scripts/hwpx_tool.py inspect result.hwpx
```

See `references/document-spec.md` for the input format, `references/feature-status.md` for support boundaries, and `SKILL.md` for agent instructions.
