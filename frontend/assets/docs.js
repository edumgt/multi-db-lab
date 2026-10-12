// 기술 문서 — 프로젝트 루트의 techNNN.md 를 /api/docs/tech 로 받아 marked 로 렌더링한다.
//  * 콘텐츠 영역(panel-docs): 좌측 목록(주제별 그룹 · 검색) + 우측 본문. 기본 보기.
//  * 우측 offcanvas(docsPanel): "옆에 띄우기" 로 다른 DB 화면과 나란히 볼 때 사용. side · wide · dock 모드.
// $(), api(), setMessage() 는 app.js 의 전역 헬퍼를 재사용한다.

const DOCS_MODE_KEY = "docsMode";
const DOC_LAST_KEY = "docsLastId";

// 주제별 그룹 — 읽기 순서 추천에도 그대로 사용
const DOC_GROUPS = [
  { name: "파이썬 기초 다지기", icon: "fa-solid fa-seedling", ids: ["tech001", "tech002", "tech003", "tech005", "tech013", "tech018"] },
  { name: "클래스와 함수", icon: "fa-solid fa-cubes", ids: ["tech004", "tech012", "tech010", "tech011"] },
  { name: "예외 · 자원 · 데이터", icon: "fa-solid fa-shield-halved", ids: ["tech006", "tech009", "tech007", "tech008", "tech014"] },
  { name: "검증 · 테스트 · 도구", icon: "fa-solid fa-flask-vial", ids: ["tech016", "tech017", "tech015"] },
];

const docsState = {
  list: [],
  byId: {},
  cache: {},
  loaded: false,
  // offcanvas
  open: false,
  mode: localStorage.getItem(DOCS_MODE_KEY) || "side",
  currentId: null,
  // 콘텐츠 영역
  contentId: null,
  filter: "",
};

window.docTitle = (docId) => docsState.byId[docId]?.title || null;

function groupOf(docId) {
  return DOC_GROUPS.find((g) => g.ids.includes(docId)) || { name: "기타", icon: "fa-solid fa-file" };
}

// ---------------------------------------------------------------------------
// 데이터
// ---------------------------------------------------------------------------
async function loadDocsList() {
  if (docsState.loaded) return;
  try {
    const list = await api("/api/docs/tech");
    docsState.list = list;
    docsState.byId = {};
    list.forEach((doc) => (docsState.byId[doc.id] = doc));
    docsState.loaded = true;
    renderDocsList();
    renderContentList();
    renderOrderChips();
    if (window.refreshDocChips) window.refreshDocChips();
  } catch (error) {
    setMessage("docsMsg", `문서 목록을 불러오지 못했습니다: ${error.message}`);
    setMessage("appMsg", `문서 목록을 불러오지 못했습니다: ${error.message}`);
  }
}

async function fetchDoc(docId) {
  if (!docsState.cache[docId]) {
    docsState.cache[docId] = await api(`/api/docs/tech/${encodeURIComponent(docId)}`);
  }
  return docsState.cache[docId];
}

// 마크다운 → HTML. 맨 위 "쉽게 이해하기" 인용문은 콜아웃 상자로 꾸민다.
function renderMarkdown(markdown) {
  const wrap = document.createElement("div");
  wrap.innerHTML = marked.parse(markdown);
  wrap.querySelectorAll("blockquote").forEach((bq) => {
    const first = bq.querySelector("p strong");
    if (first && first.textContent.trim() === "쉽게 이해하기") {
      bq.classList.add("easy-callout");
      first.insertAdjacentHTML("afterbegin", '<i class="fa-solid fa-lightbulb text-amber-500"></i> ');
    }
  });
  return wrap.innerHTML;
}

function neighbors(docId) {
  const idx = docsState.list.findIndex((d) => d.id === docId);
  return { prev: docsState.list[idx - 1], next: docsState.list[idx + 1] };
}

// ---------------------------------------------------------------------------
// 콘텐츠 영역 보기
// ---------------------------------------------------------------------------
function renderContentList() {
  const list = $("cdocList");
  list.innerHTML = "";
  const q = docsState.filter.trim().toLowerCase();
  let shown = 0;
  DOC_GROUPS.forEach((group) => {
    const docs = group.ids
      .map((id) => docsState.byId[id])
      .filter((d) => d && (!q || d.title.toLowerCase().includes(q) || d.summary.toLowerCase().includes(q)));
    if (!docs.length) return;
    const h = document.createElement("div");
    h.className = "nav-group flex items-center gap-1.5";
    h.innerHTML = `<i class="${group.icon}"></i> ${group.name}`;
    list.appendChild(h);
    docs.forEach((doc) => {
      shown += 1;
      const btn = document.createElement("button");
      btn.className = `doc-item ${doc.id === docsState.contentId ? "active" : ""}`;
      btn.dataset.doc = doc.id;
      btn.innerHTML = `
        <div class="flex items-center gap-2.5">
          <span class="w-7 h-7 rounded-lg bg-slate-100 text-slate-500 text-[11px] font-mono flex items-center justify-center shrink-0">${doc.id.slice(-2)}</span>
          <span class="font-medium text-sm text-slate-800 truncate">${doc.title}</span>
        </div>
        <p class="text-xs text-slate-500 mt-1 line-clamp-2 pl-[38px]">${doc.summary.replace(/[`*_]/g, "")}</p>`;
      btn.onclick = () => showDocInContent(doc.id);
      list.appendChild(btn);
    });
  });
  if (!shown) list.innerHTML = '<p class="text-sm text-slate-500 px-3 py-6 text-center">검색 결과가 없습니다.</p>';
}

function renderOrderChips() {
  const box = $("cdocOrder");
  box.innerHTML = "";
  DOC_GROUPS.forEach((group) => {
    group.ids.forEach((id) => {
      const doc = docsState.byId[id];
      if (!doc) return;
      const chip = document.createElement("button");
      chip.className = "chip";
      chip.innerHTML = `<span class="font-mono text-[10px] text-brand-700/70">${id.slice(-2)}</span> ${doc.title}`;
      chip.onclick = () => showDocInContent(id);
      box.appendChild(chip);
    });
  });
}

function showContentHome() {
  docsState.contentId = null;
  $("cdocReader").classList.add("hidden");
  $("cdocEmpty").classList.remove("hidden");
  document.querySelectorAll("#cdocList .doc-item").forEach((el) => el.classList.remove("active"));
}

async function showDocInContent(docId) {
  docsState.contentId = docId;
  localStorage.setItem(DOC_LAST_KEY, docId);
  $("cdocEmpty").classList.add("hidden");
  $("cdocReader").classList.remove("hidden");
  document.querySelectorAll("#cdocList .doc-item").forEach((el) => el.classList.toggle("active", el.dataset.doc === docId));
  const content = $("cdocContent");
  content.innerHTML = '<p class="text-slate-400"><i class="fa-solid fa-spinner fa-spin"></i> 불러오는 중…</p>';
  setMessage("appMsg");
  try {
    const doc = await fetchDoc(docId);
    if (docsState.contentId !== docId) return;
    const group = groupOf(docId);
    $("cdocGroup").innerHTML = `<i class="${group.icon}"></i> ${group.name}`;
    $("cdocTitle").textContent = `${doc.id} · ${doc.title}`;
    content.innerHTML = renderMarkdown(doc.content);
    const { prev, next } = neighbors(docId);
    $("cdocPrev").disabled = !prev;
    $("cdocNext").disabled = !next;
    $("cdocPrev").title = prev ? `이전: ${prev.title}` : "";
    $("cdocNext").title = next ? `다음: ${next.title}` : "";
    const el = document.querySelector('#cdocList .doc-item.active');
    if (el) el.scrollIntoView({ block: "nearest" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (error) {
    content.innerHTML = "";
    setMessage("appMsg", `문서를 불러오지 못했습니다: ${error.message}`);
  }
}

// usecases.js 가 "기술 문서" 메뉴를 열 때 호출
window.showDocsPanel = async () => {
  await loadDocsList();
  const last = docsState.contentId || localStorage.getItem(DOC_LAST_KEY);
  if (last && docsState.byId[last]) showDocInContent(last);
  else showContentHome();
};

// "관련 기술 문서" 칩 · 헤더 버튼 → 콘텐츠 영역에서 연다
window.openDocInContent = async (docId) => {
  if (docId) docsState.contentId = docId;
  if (typeof selectUseCase === "function") selectUseCase("docs");
  await loadDocsList();
  if (docId) await showDocInContent(docId);
};

// ---------------------------------------------------------------------------
// 우측 offcanvas 보기 (옆에 띄우기)
// ---------------------------------------------------------------------------
const PANEL_BASE = "bg-white border-l border-slate-200 flex flex-col transition-[transform,width] duration-200";
const PANEL_MODE = {
  side: "fixed top-0 right-0 h-full z-50 shadow-2xl w-full sm:w-[640px]",
  wide: "fixed top-0 right-0 h-full z-50 shadow-2xl w-full lg:w-[1100px] 2xl:w-[1320px]",
  dock: "sticky top-16 h-[calc(100vh-4rem)] w-full sm:w-[560px] 2xl:w-[760px] shrink-0 z-10",
};

function applyPanelLayout() {
  const panel = $("docsPanel");
  const overlay = docsState.mode !== "dock";
  let cls = `${PANEL_BASE} ${PANEL_MODE[docsState.mode]}`;
  if (overlay && !docsState.open) cls += " translate-x-full";
  if (!overlay && !docsState.open) cls += " hidden";
  panel.className = cls;
  $("docsBackdrop").classList.toggle("hidden", !(overlay && docsState.open));
  document.body.classList.toggle("overflow-hidden", overlay && docsState.open);
  ["side", "wide", "dock"].forEach((mode) => {
    const btn = $(`docsMode${mode[0].toUpperCase()}${mode.slice(1)}`);
    btn.classList.toggle("text-brand-600", docsState.mode === mode);
    btn.classList.toggle("bg-brand-50", docsState.mode === mode);
  });
}

function docsSetOpen(open) {
  docsState.open = open;
  applyPanelLayout();
}

function docsSetMode(mode) {
  docsState.mode = mode;
  localStorage.setItem(DOCS_MODE_KEY, mode);
  applyPanelLayout();
}

function docsShowList() {
  docsState.currentId = null;
  $("docsBack").classList.add("hidden");
  $("docsHeading").textContent = "기술 문서";
  $("docsContent").classList.add("hidden");
  $("docsList").classList.remove("hidden");
  document.querySelectorAll("#docsList .doc-item").forEach((el) => el.classList.remove("active"));
}

function renderDocsList() {
  const list = $("docsList");
  list.innerHTML = "";
  $("docsCount").textContent = `${docsState.list.length}편`;
  DOC_GROUPS.forEach((group) => {
    const h = document.createElement("div");
    h.className = "nav-group flex items-center gap-1.5";
    h.innerHTML = `<i class="${group.icon}"></i> ${group.name}`;
    list.appendChild(h);
    group.ids.forEach((id) => {
      const doc = docsState.byId[id];
      if (!doc) return;
      const btn = document.createElement("button");
      btn.className = "doc-item";
      btn.dataset.doc = doc.id;
      btn.innerHTML = `
        <div class="flex items-center gap-2.5">
          <span class="w-7 h-7 rounded-lg bg-slate-100 text-slate-500 text-[11px] font-mono flex items-center justify-center shrink-0">${doc.id.slice(-2)}</span>
          <span class="font-medium text-sm text-slate-800 truncate">${doc.title}</span>
          <i class="fa-solid fa-chevron-right text-xs text-slate-300 ml-auto"></i>
        </div>`;
      btn.onclick = () => showDoc(doc.id);
      list.appendChild(btn);
    });
  });
}

async function showDoc(docId) {
  setMessage("docsMsg");
  $("docsBack").classList.remove("hidden");
  $("docsList").classList.add("hidden");
  const content = $("docsContent");
  content.classList.remove("hidden");
  content.innerHTML = '<p class="text-slate-400"><i class="fa-solid fa-spinner fa-spin"></i> 불러오는 중…</p>';
  docsState.currentId = docId;
  document.querySelectorAll("#docsList .doc-item").forEach((el) => el.classList.toggle("active", el.dataset.doc === docId));
  try {
    const doc = await fetchDoc(docId);
    if (docsState.currentId !== docId) return;
    $("docsHeading").textContent = `${doc.id} · ${doc.title}`;
    content.innerHTML = `<div class="max-w-4xl mx-auto">${renderMarkdown(doc.content)}</div>`;
    content.scrollTop = 0;
    const { prev, next } = neighbors(docId);
    const navBar = document.createElement("div");
    navBar.className = "max-w-4xl mx-auto flex justify-between gap-2 mt-8 pt-4 border-t border-slate-200 text-xs";
    navBar.innerHTML = `
      <button ${prev ? "" : "disabled"} class="btn-ghost !text-xs"><i class="fa-solid fa-chevron-left"></i> ${prev ? prev.title : ""}</button>
      <button ${next ? "" : "disabled"} class="btn-ghost !text-xs">${next ? next.title : ""} <i class="fa-solid fa-chevron-right"></i></button>`;
    const [prevBtn, nextBtn] = navBar.querySelectorAll("button");
    if (prev) prevBtn.onclick = () => showDoc(prev.id);
    if (next) nextBtn.onclick = () => showDoc(next.id);
    content.appendChild(navBar);
  } catch (error) {
    content.innerHTML = "";
    setMessage("docsMsg", `문서를 불러오지 못했습니다: ${error.message}`);
  }
}

// 외부에서 offcanvas 로 특정 문서를 연다 (콘텐츠 리더의 "옆에 띄우기")
window.openDoc = async (docId) => {
  docsSetOpen(true);
  await loadDocsList();
  if (docId) await showDoc(docId);
  else docsShowList();
};

// ---------------------------------------------------------------------------
// 이벤트
// ---------------------------------------------------------------------------
$("btnDocs").onclick = () => window.openDocInContent(null);
$("cdocSearch").oninput = (event) => {
  docsState.filter = event.target.value;
  renderContentList();
};
$("cdocHome").onclick = showContentHome;
$("cdocPrev").onclick = () => {
  const { prev } = neighbors(docsState.contentId);
  if (prev) showDocInContent(prev.id);
};
$("cdocNext").onclick = () => {
  const { next } = neighbors(docsState.contentId);
  if (next) showDocInContent(next.id);
};
$("cdocSide").onclick = () => window.openDoc(docsState.contentId);

$("docsClose").onclick = () => docsSetOpen(false);
$("docsBackdrop").onclick = () => docsSetOpen(false);
$("docsBack").onclick = docsShowList;
$("docsModeSide").onclick = () => docsSetMode("side");
$("docsModeWide").onclick = () => docsSetMode("wide");
$("docsModeDock").onclick = () => docsSetMode("dock");
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && docsState.open && docsState.mode !== "dock") docsSetOpen(false);
});

// 로그인 직후 usecases.js 가 호출 — 칩 라벨용으로 목록을 미리 받아 둔다.
window.preloadDocs = loadDocsList;
applyPanelLayout();
