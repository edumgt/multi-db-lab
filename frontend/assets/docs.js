// 우측 문서 패널 — 프로젝트 루트의 techNNN.md 를 /api/docs/tech 로 받아 marked 로 렌더링한다.
// 표시 모드 3 가지: side(사이드 오버레이) · wide(확대 오버레이) · dock(콘텐츠 영역 옆에 도킹, 본문과 나란히 봄)
// $(), api(), setMessage() 는 app.js 의 전역 헬퍼를 재사용한다.

const DOCS_MODE_KEY = "docsMode";

const docsState = {
  list: [],
  byId: {},
  open: false,
  mode: localStorage.getItem(DOCS_MODE_KEY) || "side",
  currentId: null,
  loaded: false,
};

const PANEL_BASE = "bg-white border-l border-slate-200 flex flex-col transition-[transform,width] duration-200";
const PANEL_MODE = {
  side: "fixed top-0 right-0 h-full z-50 shadow-2xl w-full sm:w-[640px]",
  wide: "fixed top-0 right-0 h-full z-50 shadow-2xl w-full lg:w-[1100px] 2xl:w-[1320px]",
  dock: "sticky top-16 h-[calc(100vh-4rem)] w-full sm:w-[560px] 2xl:w-[760px] shrink-0 z-10",
};

window.docTitle = (docId) => docsState.byId[docId]?.title || null;

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
  docsState.list.forEach((doc, idx) => {
    const btn = document.createElement("button");
    btn.className = "doc-item";
    btn.dataset.doc = doc.id;
    btn.innerHTML = `
      <div class="flex items-center gap-2.5">
        <span class="w-7 h-7 rounded-lg bg-slate-100 text-slate-500 text-[11px] font-mono flex items-center justify-center shrink-0">${String(idx + 1).padStart(2, "0")}</span>
        <span class="font-medium text-sm text-slate-800 truncate">${doc.title}</span>
        <i class="fa-solid fa-chevron-right text-xs text-slate-300 ml-auto"></i>
      </div>
      <p class="text-xs text-slate-500 mt-1 line-clamp-2 pl-[38px]">${doc.summary.replace(/[`*_]/g, "")}</p>`;
    btn.onclick = () => showDoc(doc.id);
    list.appendChild(btn);
  });
}

async function loadDocsList() {
  if (docsState.loaded) return;
  setMessage("docsMsg");
  try {
    const list = await api("/api/docs/tech");
    docsState.list = list;
    docsState.byId = {};
    list.forEach((doc) => (docsState.byId[doc.id] = doc));
    docsState.loaded = true;
    renderDocsList();
    if (window.refreshDocChips) window.refreshDocChips();
  } catch (error) {
    setMessage("docsMsg", `문서 목록을 불러오지 못했습니다: ${error.message}`);
  }
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
    const doc = await api(`/api/docs/tech/${encodeURIComponent(docId)}`);
    if (docsState.currentId !== docId) return;
    $("docsHeading").textContent = `${doc.id} · ${doc.title}`;
    content.innerHTML = `<div class="max-w-4xl mx-auto">${marked.parse(doc.content)}</div>`;
    content.scrollTop = 0;

    const idx = docsState.list.findIndex((d) => d.id === docId);
    const prev = docsState.list[idx - 1];
    const next = docsState.list[idx + 1];
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

// 외부(usecases.js 의 "관련 문서" 칩) 에서 특정 문서를 바로 연다.
window.openDoc = async (docId) => {
  docsSetOpen(true);
  await loadDocsList();
  if (docId) await showDoc(docId);
  else docsShowList();
};

$("btnDocs").onclick = async () => {
  if (docsState.open) {
    docsSetOpen(false);
    return;
  }
  docsSetOpen(true);
  await loadDocsList();
  if (!docsState.currentId) docsShowList();
};
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
