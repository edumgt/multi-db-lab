// DB 별 사용 사례 패널 — 좌측 내비게이션에서 DB 를 고르면 그 DB 에 어울리는 시나리오 UI 를 보여준다.
// 패널 종류: posts(ORM 게시판) · records(7 개 레코드 저장소 공통) · employees(DynamoDB) · vector · graph · engine

const USE_CASES = [
  {
    key: "posts", panel: "posts", icon: "fa-solid fa-database", color: "bg-sky-100 text-sky-700", label: "PostgreSQL", category: "관계형 · ORM",
    title: "PostgreSQL + SQLAlchemy ORM — 게시판", endpoint: "/api/posts",
    useCase: "사용 사례: 트랜잭션이 중요한 핵심 업무 데이터 (사용자 · 게시글 · 권한)",
    desc: "외래키(owner) · 정렬 · 페이지네이션 · 조회수 증가처럼 정합성과 조인이 필요한 데이터는 RDBMS 가 기본 선택입니다. ORM 세션이 요청 단위로 열리고 커밋/롤백됩니다.",
    docs: ["tech009", "tech012", "tech003", "tech011"],
  },
  {
    key: "postgres", panel: "records", source: "postgres", icon: "fa-solid fa-table-cells", color: "bg-sky-100 text-sky-700", label: "PostgreSQL (Core)", category: "관계형 · SQLAlchemy Core",
    title: "PostgreSQL + SQLAlchemy Core — lab_records 테이블", endpoint: "/lab/postgres/records",
    useCase: "사용 사례: ORM 없이 테이블/SQL 을 직접 다루는 배치 · 리포팅 레이어",
    desc: "같은 PostgreSQL 이지만 Core API 로 Table 객체와 insert/select 문을 직접 조립합니다. tags 는 ARRAY 컬럼에 저장되며 `with engine.begin()` 이 트랜잭션 경계를 만듭니다.",
    docs: ["tech009", "tech013", "tech006"],
  },
  {
    key: "mongo", panel: "records", source: "mongo", icon: "fa-solid fa-leaf", color: "bg-emerald-100 text-emerald-700", label: "MongoDB", category: "문서(Document)",
    title: "MongoDB — 스키마가 유연한 문서 저장", endpoint: "/lab/mongo/records",
    useCase: "사용 사례: 필드가 자주 바뀌는 콘텐츠 · 카탈로그 · 이벤트 페이로드",
    desc: "레코드를 JSON 문서 그대로 저장합니다. tags 배열도 중첩 구조 그대로 들어가므로 조인 없이 한 번에 읽습니다. 드라이버 예외는 도메인 예외(ExternalServiceError) 로 번역됩니다.",
    docs: ["tech006", "tech004", "tech005"],
  },
  {
    key: "supabase", panel: "records", source: "supabase", icon: "fa-solid fa-bolt", color: "bg-lime-100 text-lime-700", label: "Supabase", category: "BaaS · PostgREST",
    title: "Supabase — HTTP API 로 쓰는 PostgreSQL", endpoint: "/lab/supabase/records",
    useCase: "사용 사례: 백엔드 인프라 없이 빠르게 시작하는 프로토타입 · 모바일 백엔드",
    desc: "supabase-py 는 PostgREST 를 감싸므로 DB 커넥션이 아니라 HTTPS 요청으로 동작합니다. 같은 LabRecordRepository 포트를 구현해 다른 저장소와 교체 가능합니다.",
    docs: ["tech006", "tech016", "tech004"],
  },
  {
    key: "redis", panel: "records", source: "redis", icon: "fa-solid fa-memory", color: "bg-rose-100 text-rose-700", label: "Redis", category: "키-값 · 인메모리",
    title: "Redis — 캐시 · 세션 · 빠른 키-값 조회", endpoint: "/lab/redis/records",
    useCase: "사용 사례: 세션 · 캐시 · 순위표 · 짧은 수명의 상태 (밀리초 응답)",
    desc: "레코드를 JSON 문자열로 직렬화해 `prefix:id` 키에 저장합니다. 목록은 SCAN 으로 키를 순회(scan_iter 제너레이터)하므로 큰 키 공간에서도 서버를 막지 않습니다.",
    docs: ["tech007", "tech011", "tech018"],
  },
  {
    key: "opensearch", panel: "records", source: "opensearch", icon: "fa-solid fa-magnifying-glass", color: "bg-cyan-100 text-cyan-700", label: "OpenSearch", category: "검색 엔진",
    title: "OpenSearch — 전문 검색 · 로그 인덱싱", endpoint: "/lab/opensearch/records",
    useCase: "사용 사례: 본문 검색 · 로그/이벤트 분석 · 자동 완성",
    desc: "레코드는 역색인(inverted index) 으로 색인됩니다. 저장 직후 검색에 반영되도록 refresh 를 사용하고, 조회는 match_all 쿼리로 수행합니다.",
    docs: ["tech006", "tech014", "tech016"],
  },
  {
    key: "clickhouse", panel: "records", source: "clickhouse", icon: "fa-solid fa-chart-column", color: "bg-amber-100 text-amber-700", label: "ClickHouse", category: "OLAP · 컬럼 지향",
    title: "ClickHouse — 대량 분석 쿼리 (OLAP)", endpoint: "/lab/clickhouse/records",
    useCase: "사용 사례: 수억 건 이벤트 집계 · 대시보드 · 시계열 분석",
    desc: "컬럼 지향 저장으로 집계가 빠르지만 행 단위 UPDATE/DELETE 는 비용이 큽니다(ALTER ... UPDATE 변이). SQL 은 파라미터 바인딩 `{name:Type}` 플레이스홀더를 씁니다.",
    docs: ["tech018", "tech006", "tech013"],
  },
  {
    key: "cassandra", panel: "records", source: "cassandra", icon: "fa-solid fa-layer-group", color: "bg-violet-100 text-violet-700", label: "Cassandra", category: "와이드 컬럼 · 분산",
    title: "Cassandra — 쓰기 집중 · 다중 리전 분산", endpoint: "/lab/cassandra/records",
    useCase: "사용 사례: IoT · 메시지 · 활동 로그처럼 쓰기가 많고 단일 장애점이 없어야 하는 데이터",
    desc: "파티션 키 기준으로 데이터가 노드에 분산됩니다. CQL 은 SQL 과 비슷하지만 조인이 없고, `?` 플레이스홀더로 바인딩합니다. 조회는 파티션 키 설계가 성능을 좌우합니다.",
    docs: ["tech018", "tech013", "tech006"],
  },
  {
    key: "dynamodb", panel: "employees", icon: "fa-brands fa-aws", color: "bg-orange-100 text-orange-700", label: "DynamoDB", category: "서버리스 키-값",
    title: "DynamoDB — 파티션 키 + 정렬 키로 직원 관리", endpoint: "/employees",
    useCase: "사용 사례: 서버리스 · 예측 가능한 지연 시간 · 키 기반 접근 (id + name 복합 키)",
    desc: "조회는 반드시 키(id, name) 로 하고, 전체 목록은 Scan 입니다. 스키마 없는 아이템이지만 접근 패턴을 먼저 정해 키를 설계해야 합니다.",
    docs: ["tech004", "tech012", "tech006"],
  },
  {
    key: "vector", panel: "vector", icon: "fa-solid fa-vector-square", color: "bg-fuchsia-100 text-fuchsia-700", label: "Vector DB", category: "Pinecone · Weaviate · Qdrant",
    title: "벡터 DB — 임베딩 유사도 검색", endpoint: "/lab/vector/*",
    useCase: "사용 사례: RAG 검색 · 추천 · 유사 이미지/문장 찾기",
    desc: "숫자 벡터(임베딩) 를 저장하고 코사인/내적 유사도로 top-k 를 찾습니다. 서버 설정 APP_VECTOR_PROVIDER 에 따라 Pinecone · Weaviate · Qdrant 중 하나가 전략 테이블에서 선택됩니다.",
    docs: ["tech010", "tech005", "tech004"],
  },
  {
    key: "graph", panel: "graph", icon: "fa-solid fa-diagram-project", color: "bg-indigo-100 text-indigo-700", label: "Neo4j", category: "그래프",
    title: "Neo4j — 관계 분석 (PageRank · Degree)", endpoint: "/lab/graph/*",
    useCase: "사용 사례: 소셜 네트워크 · 추천 · 사기 탐지 · 지식 그래프",
    desc: "노드와 엣지를 Cypher 로 저장하고, 영향력(PageRank) 이나 연결 수(Degree) 를 계산해 순위를 냅니다. 다단계 관계 탐색이 RDBMS 조인보다 자연스럽습니다.",
    docs: ["tech005", "tech016", "tech006"],
  },
  {
    key: "engine", panel: "engine", icon: "fa-solid fa-puzzle-piece", color: "bg-slate-200 text-slate-700", label: "멀티 DB 엔진", category: "통합",
    title: "멀티 DB 엔진 — 여러 저장소를 하나의 Grid 로", endpoint: "/lab/{source}/records",
    useCase: "사용 사례: 폴리글랏 퍼시스턴스 — 같은 포트(LabRecordRepository) 를 구현한 저장소를 런타임에 합치기",
    desc: "캔버스에서 DB 노드를 Grid 에 연결하면 각 저장소의 레코드를 가져와 합쳐 보여줍니다. 구조가 다른 DB(Employee/Vector/Graph) 는 연결되지 않습니다.",
    docs: ["tech010", "tech004", "tech011"],
  },
];

const UC_KEY = "useCaseKey";
const NAV_KEY = "navCollapsed";
const NAV_DESKTOP = 1280; // tailwind xl

// 좌측 offcanvas — 데스크톱(xl+) 은 접기/펼치기, 그 아래는 슬라이드 오버레이
function setNav(open) {
  const nav = $("useCaseNav");
  if (window.innerWidth >= NAV_DESKTOP) {
    nav.classList.toggle("xl:!hidden", !open);
    nav.classList.add("-translate-x-full");
    $("navBackdrop").classList.add("hidden");
    localStorage.setItem(NAV_KEY, open ? "0" : "1");
  } else {
    nav.classList.remove("xl:!hidden");
    nav.classList.toggle("-translate-x-full", !open);
    $("navBackdrop").classList.toggle("hidden", !open);
  }
}

function isNavOpen() {
  const nav = $("useCaseNav");
  if (window.innerWidth >= NAV_DESKTOP) return !nav.classList.contains("xl:!hidden");
  return !nav.classList.contains("-translate-x-full");
}
const ucState = {
  current: null,
  source: null,
  recGridApi: null,
  empGridApi: null,
  vecGridApi: null,
  graphGridApi: null,
  recEditId: null,
};

const META = (() => {
  const map = {};
  USE_CASES.forEach((uc) => (map[uc.key] = uc));
  return map;
})();

function parseTags(text) {
  return text.split(",").map((t) => t.trim()).filter(Boolean);
}

function parseVector(text) {
  const values = text.split(",").map((t) => Number(t.trim())).filter((n) => !Number.isNaN(n));
  if (!values.length) throw new Error("values 에 쉼표로 구분한 실수를 입력해 주세요.");
  return values;
}

function randomId(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

// ---------------------------------------------------------------------------
// 내비게이션 / 패널 전환
// ---------------------------------------------------------------------------
function buildNav() {
  const nav = $("navItems");
  nav.innerHTML = "";
  const groups = [
    ["관계형", ["posts", "postgres"]],
    ["NoSQL 레코드 저장소", ["mongo", "supabase", "redis", "opensearch", "clickhouse", "cassandra"]],
    ["키-값 · 서버리스", ["dynamodb"]],
    ["벡터 · 그래프", ["vector", "graph"]],
    ["통합", ["engine"]],
  ];
  groups.forEach(([heading, keys]) => {
    const h = document.createElement("div");
    h.className = "nav-group";
    h.textContent = heading;
    nav.appendChild(h);
    keys.forEach((key) => {
      const uc = META[key];
      const btn = document.createElement("button");
      btn.className = "nav-item";
      btn.dataset.key = key;
      btn.innerHTML = `<span class="nav-icon ${uc.color}"><i class="${uc.icon}"></i></span><span class="min-w-0"><span class="block truncate">${uc.label}</span><span class="nav-sub">${uc.category}</span></span>`;
      btn.onclick = () => {
        selectUseCase(key);
        if (window.innerWidth < NAV_DESKTOP) setNav(false);
      };
      nav.appendChild(btn);
    });
  });
}

function renderHeader(uc) {
  $("ucIcon").className = `w-14 h-14 rounded-2xl flex items-center justify-center text-2xl shrink-0 ${uc.color}`;
  $("ucIcon").innerHTML = `<i class="${uc.icon}"></i>`;
  $("ucTitle").textContent = uc.title;
  $("ucCategory").textContent = uc.category;
  $("ucEndpoint").textContent = uc.endpoint;
  $("ucUseCase").textContent = uc.useCase;
  $("ucDesc").textContent = uc.desc;
  const docs = $("ucDocs");
  docs.innerHTML = "";
  uc.docs.forEach((docId) => {
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.innerHTML = `<i class="fa-regular fa-file-lines"></i><span>${(window.docTitle && window.docTitle(docId)) || docId}</span>`;
    chip.dataset.doc = docId;
    chip.onclick = () => window.openDoc && window.openDoc(docId);
    docs.appendChild(chip);
  });
}

function selectUseCase(key) {
  const uc = META[key] || META.posts;
  ucState.current = uc.key;
  localStorage.setItem(UC_KEY, uc.key);
  setMessage("appMsg");

  document.querySelectorAll("#useCaseNav .nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.key === uc.key);
  });
  document.querySelectorAll("main .panel").forEach((el) => el.classList.add("hidden"));
  $(`panel-${uc.panel}`).classList.remove("hidden");
  renderHeader(uc);

  if (uc.panel === "posts") loadPosts();
  if (uc.panel === "records") {
    ucState.source = uc.source;
    loadRecords();
  }
  if (uc.panel === "employees") loadEmployees();
  if (uc.panel === "vector") $("vecProvider").textContent = "";
  if (uc.panel === "engine" && typeof window.ensureEngine === "function") window.ensureEngine();
}

// ---------------------------------------------------------------------------
// Lab 레코드 저장소 (7 개 DB 공통)
// ---------------------------------------------------------------------------
function recordEndpoint() {
  return `/lab/${ucState.source}/records`;
}

const recColumnDefs = [
  { field: "source", width: 110 },
  { field: "id", width: 200 },
  { field: "title", flex: 1 },
  { field: "content", flex: 2 },
  { headerName: "tags", width: 180, valueGetter: (p) => (p.data.tags || []).join(", ") },
  {
    headerName: "액션", width: 150,
    cellRenderer: (params) => {
      const wrap = document.createElement("div");
      wrap.className = "h-full flex items-center gap-1";
      const edit = document.createElement("button");
      edit.textContent = "수정";
      edit.className = "text-xs px-2 py-1 rounded bg-amber-500 text-white";
      edit.onclick = () => openRecordEditor(params.data);
      const del = document.createElement("button");
      del.textContent = "삭제";
      del.className = "text-xs px-2 py-1 rounded bg-rose-600 text-white";
      del.onclick = () => deleteRecord(params.data.id);
      wrap.append(edit, del);
      return wrap;
    },
  },
];

async function loadRecords() {
  if (!ucState.source) return;
  const source = ucState.source;
  await withLoading(async () => {
    const limit = Number($("recLimit").value) || 50;
    const rows = await api(`${recordEndpoint()}?limit=${limit}`);
    if (ucState.source === source) ucState.recGridApi.setGridOption("rowData", rows);
  }).catch((error) => {
    ucState.recGridApi.setGridOption("rowData", []);
    setMessage("appMsg", `${META[ucState.current].label} 조회 실패: ${error.message}`);
  });
}

async function createRecord(payload) {
  setMessage("appMsg");
  await withLoading(async () => {
    await api(recordEndpoint(), { method: "POST", body: JSON.stringify(payload) });
  }).catch((error) => setMessage("appMsg", `추가 실패: ${error.message}`));
  await loadRecords();
}

function openRecordEditor(row) {
  ucState.recEditId = row.id;
  $("recEditorTitle").textContent = `${row.source} 레코드 수정 — ${row.id}`;
  $("recEditTitle").value = row.title || "";
  $("recEditContent").value = row.content || "";
  $("recEditTags").value = (row.tags || []).join(", ");
  $("recEditor").showModal();
}

async function saveRecord() {
  const payload = {
    title: $("recEditTitle").value.trim() || null,
    content: $("recEditContent").value.trim() || null,
    tags: parseTags($("recEditTags").value),
  };
  await withLoading(async () => {
    await api(`${recordEndpoint()}/${encodeURIComponent(ucState.recEditId)}`, {
      method: "PATCH", body: JSON.stringify(payload),
    });
    $("recEditor").close();
  }).catch((error) => setMessage("appMsg", `수정 실패: ${error.message}`));
  await loadRecords();
}

async function deleteRecord(id) {
  if (!confirm(`${id} 를 삭제하시겠습니까?`)) return;
  await withLoading(async () => {
    await api(`${recordEndpoint()}/${encodeURIComponent(id)}`, { method: "DELETE" });
  }).catch((error) => setMessage("appMsg", `삭제 실패: ${error.message}`));
  await loadRecords();
}

// ---------------------------------------------------------------------------
// DynamoDB 직원
// ---------------------------------------------------------------------------
const empColumnDefs = [
  { field: "id", width: 160 },
  { field: "name", flex: 1 },
  { field: "position", flex: 1 },
  {
    headerName: "액션", width: 120,
    cellRenderer: (params) => {
      const del = document.createElement("button");
      del.textContent = "삭제";
      del.className = "text-xs px-2 py-1 rounded bg-rose-600 text-white";
      del.onclick = () => deleteEmployee(params.data);
      return del;
    },
  },
];

async function loadEmployees() {
  await withLoading(async () => {
    const rows = await api("/employees");
    ucState.empGridApi.setGridOption("rowData", rows);
  }).catch((error) => {
    ucState.empGridApi.setGridOption("rowData", []);
    setMessage("appMsg", `DynamoDB 조회 실패: ${error.message}`);
  });
}

async function createEmployee() {
  const payload = {
    id: $("empId").value.trim(), name: $("empName").value.trim(), position: $("empPosition").value.trim(),
  };
  if (!payload.id || !payload.name || !payload.position) {
    setMessage("appMsg", "id · name · position 을 모두 입력해 주세요.");
    return;
  }
  setMessage("appMsg");
  await withLoading(async () => {
    const res = await api("/employees", { method: "POST", body: JSON.stringify(payload) });
    $("empResult").textContent = JSON.stringify(res, null, 2);
  }).catch((error) => setMessage("appMsg", `추가 실패: ${error.message}`));
  await loadEmployees();
}

async function getEmployee() {
  const id = $("empId").value.trim();
  const name = $("empName").value.trim();
  if (!id || !name) {
    setMessage("appMsg", "키 조회에는 id 와 name 이 모두 필요합니다 (파티션 키 + 정렬 키).");
    return;
  }
  setMessage("appMsg");
  await withLoading(async () => {
    const res = await api(`/employees/${encodeURIComponent(id)}/${encodeURIComponent(name)}`);
    $("empResult").textContent = JSON.stringify(res, null, 2);
  }).catch((error) => {
    $("empResult").textContent = "";
    setMessage("appMsg", `조회 실패: ${error.message}`);
  });
}

async function deleteEmployee(row) {
  if (!confirm(`${row.id} / ${row.name} 을 삭제하시겠습니까?`)) return;
  await withLoading(async () => {
    await api(`/employees/${encodeURIComponent(row.id)}/${encodeURIComponent(row.name)}`, { method: "DELETE" });
  }).catch((error) => setMessage("appMsg", `삭제 실패: ${error.message}`));
  await loadEmployees();
}

// ---------------------------------------------------------------------------
// Vector DB
// ---------------------------------------------------------------------------
const vecColumnDefs = [
  { field: "id", width: 180 },
  { field: "score", width: 140, valueFormatter: (p) => (p.value == null ? "-" : Number(p.value).toFixed(4)) },
  { headerName: "payload", flex: 1, valueGetter: (p) => JSON.stringify(p.data.payload || {}) },
];

async function upsertVector(payload) {
  setMessage("appMsg");
  return withLoading(async () => {
    const res = await api("/lab/vector/upsert", { method: "POST", body: JSON.stringify(payload) });
    $("vecProvider").textContent = `provider: ${res.provider} · ${res.id} ${res.status}`;
    return res;
  }).catch((error) => setMessage("appMsg", `업서트 실패: ${error.message}`));
}

async function queryVector() {
  setMessage("appMsg");
  await withLoading(async () => {
    const payload = { values: parseVector($("vecQuery").value), top_k: Number($("vecTopK").value) || 3 };
    const res = await api("/lab/vector/query", { method: "POST", body: JSON.stringify(payload) });
    $("vecProvider").textContent = `provider: ${res.provider} · ${res.matches.length}건`;
    ucState.vecGridApi.setGridOption("rowData", res.matches);
  }).catch((error) => {
    ucState.vecGridApi.setGridOption("rowData", []);
    setMessage("appMsg", `검색 실패: ${error.message}`);
  });
}

const VECTOR_SAMPLES = [
  { id: "doc-sports", values: [0.9, 0.1, 0.0, 0.1], metadata: { title: "축구 경기 결과", topic: "sports" } },
  { id: "doc-tech", values: [0.1, 0.9, 0.1, 0.0], metadata: { title: "파이썬 타입 힌트", topic: "tech" } },
  { id: "doc-food", values: [0.0, 0.1, 0.9, 0.1], metadata: { title: "김치찌개 레시피", topic: "food" } },
  { id: "doc-travel", values: [0.1, 0.0, 0.1, 0.9], metadata: { title: "제주 여행 코스", topic: "travel" } },
];

// ---------------------------------------------------------------------------
// Graph (Neo4j)
// ---------------------------------------------------------------------------
const graphColumnDefs = [
  { headerName: "#", width: 70, valueGetter: (p) => p.node.rowIndex + 1 },
  { field: "id", flex: 1 },
  { field: "score", width: 160, valueFormatter: (p) => Number(p.value).toFixed(4) },
];

function graphLog(line) {
  const el = $("graphLog");
  el.textContent = `${line}\n${el.textContent}`.split("\n").slice(0, 12).join("\n");
}

async function addGraphNode(payload) {
  setMessage("appMsg");
  return withLoading(async () => {
    const res = await api("/lab/graph/nodes", { method: "POST", body: JSON.stringify(payload) });
    graphLog(`노드 추가: ${res.id} (${res.label})`);
  }).catch((error) => setMessage("appMsg", `노드 추가 실패: ${error.message}`));
}

async function addGraphEdge(payload) {
  setMessage("appMsg");
  return withLoading(async () => {
    const res = await api("/lab/graph/edges", { method: "POST", body: JSON.stringify(payload) });
    graphLog(`엣지 추가: ${res.source} → ${res.target} (w=${res.weight})`);
  }).catch((error) => setMessage("appMsg", `엣지 추가 실패: ${error.message}`));
}

async function analyzeGraph() {
  setMessage("appMsg");
  await withLoading(async () => {
    const algorithm = $("gAlgo").value;
    const res = await api("/lab/graph/analyze", { method: "POST", body: JSON.stringify({ algorithm }) });
    ucState.graphGridApi.setGridOption("rowData", res.top_nodes);
    graphLog(`분석(${res.algorithm}): 상위 ${res.top_nodes.length}개 노드`);
  }).catch((error) => {
    ucState.graphGridApi.setGridOption("rowData", []);
    setMessage("appMsg", `분석 실패: ${error.message}`);
  });
}

const GRAPH_SAMPLE = {
  nodes: [["alice", "Person"], ["bob", "Person"], ["carol", "Person"], ["dave", "Person"], ["python", "Topic"]],
  edges: [["alice", "bob", 1], ["bob", "carol", 1], ["carol", "alice", 1], ["dave", "alice", 2], ["alice", "python", 1], ["bob", "python", 1]],
};

// ---------------------------------------------------------------------------
// 초기화
// ---------------------------------------------------------------------------
function makeGrid(id, columnDefs) {
  return agGrid.createGrid($(id), {
    theme: "legacy", columnDefs, rowData: [], defaultColDef: { sortable: true, resizable: true },
  });
}

function initUseCases() {
  ucState.recGridApi = makeGrid("recGrid", recColumnDefs);
  ucState.empGridApi = makeGrid("empGrid", empColumnDefs);
  ucState.vecGridApi = makeGrid("vecGrid", vecColumnDefs);
  ucState.graphGridApi = makeGrid("graphGrid", graphColumnDefs);
  buildNav();

  $("btnNav").onclick = () => setNav(!isNavOpen());
  $("navBackdrop").onclick = () => setNav(false);
  if (localStorage.getItem(NAV_KEY) === "1" && window.innerWidth >= NAV_DESKTOP) setNav(false);

  // records
  $("btnRecReload").onclick = loadRecords;
  $("btnRecCreate").onclick = () => {
    const title = $("recTitle").value.trim();
    const content = $("recContent").value.trim();
    if (!title || !content) {
      setMessage("appMsg", "title 과 content 를 입력해 주세요.");
      return;
    }
    createRecord({
      id: $("recId").value.trim() || randomId(ucState.source),
      title, content, tags: parseTags($("recTags").value),
    }).then(() => {
      ["recId", "recTitle", "recContent", "recTags"].forEach((id) => ($(id).value = ""));
    });
  };
  $("btnRecSample").onclick = async () => {
    const label = META[ucState.current].label;
    for (let i = 1; i <= 3; i += 1) {
      await createRecord({
        id: randomId(ucState.source),
        title: `${label} 샘플 ${i}`,
        content: `${label} 사용 사례 데모용 레코드 #${i}`,
        tags: ["sample", ucState.source],
      });
    }
  };
  $("btnRecSave").onclick = async (event) => {
    event.preventDefault();
    await saveRecord();
  };

  // employees
  $("btnEmpCreate").onclick = createEmployee;
  $("btnEmpGet").onclick = getEmployee;
  $("btnEmpReload").onclick = loadEmployees;

  // vector
  $("btnVecUpsert").onclick = async () => {
    try {
      const metaText = $("vecMeta").value.trim();
      await upsertVector({
        id: $("vecId").value.trim() || randomId("vec"),
        values: parseVector($("vecValues").value),
        metadata: metaText ? JSON.parse(metaText) : {},
      });
    } catch (error) {
      setMessage("appMsg", `입력 오류: ${error.message}`);
    }
  };
  $("btnVecSample").onclick = async () => {
    for (const sample of VECTOR_SAMPLES) await upsertVector(sample);
    $("vecQuery").value = "0.8, 0.2, 0.0, 0.1";
  };
  $("btnVecQuery").onclick = queryVector;

  // graph
  $("btnGNode").onclick = () => {
    const id = $("gNodeId").value.trim();
    if (!id) return setMessage("appMsg", "노드 id 를 입력해 주세요.");
    addGraphNode({ id, label: $("gNodeLabel").value.trim() || "Entity" });
  };
  $("btnGEdge").onclick = () => {
    const source = $("gEdgeSrc").value.trim();
    const target = $("gEdgeDst").value.trim();
    if (!source || !target) return setMessage("appMsg", "source 와 target 을 입력해 주세요.");
    addGraphEdge({ source, target, weight: Number($("gEdgeW").value) || 1 });
  };
  $("btnGAnalyze").onclick = analyzeGraph;
  $("btnGSample").onclick = async () => {
    for (const [id, label] of GRAPH_SAMPLE.nodes) await addGraphNode({ id, label });
    for (const [source, target, weight] of GRAPH_SAMPLE.edges) await addGraphEdge({ source, target, weight });
    await analyzeGraph();
  };
}

window.onAppShown = () => {
  selectUseCase(localStorage.getItem(UC_KEY) || "posts");
  // 문서 목록을 미리 받아 "관련 문서" 칩에 제목을 표시한다 (docs.js 가 정의).
  if (typeof window.preloadDocs === "function") window.preloadDocs();
};

// 문서 제목이 나중에 로드되면 칩 라벨을 갱신한다 (docs.js 가 호출).
window.refreshDocChips = () => {
  document.querySelectorAll("#ucDocs .chip").forEach((chip) => {
    chip.querySelector("span").textContent = (window.docTitle && window.docTitle(chip.dataset.doc)) || chip.dataset.doc;
  });
};

initUseCases();
