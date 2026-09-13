(() => {
  const provinceOrder = [
    "서울", "경기", "인천", "충청", "대전", "세종", "대구",
    "울산", "부산", "경상", "광주", "전라", "강원", "제주"
  ];
  const subjectSuffix = /\s+(?:고등(?:수학|영어|영수)|국영수).*$/;
  const normalizeSearch = (value) => value.normalize("NFKC")
    .toLocaleLowerCase("ko-KR").replace(/\s+/g, " ").trim();

  document.querySelectorAll(".directory-page .academy-directory").forEach((directory) => {
    const originalBlocks = Array.from(directory.querySelectorAll(".region-block"));
    if (!originalBlocks.length) return;

    const regions = new Map();
    const anchors = [];
    const searchableByAnchor = new Map();

    originalBlocks.forEach((block) => {
      const regionTitle = block.querySelector(".region-title h3")?.textContent.trim() || "기타";
      const province = regionTitle.split(/\s+/)[0];

      block.querySelectorAll(".local-button-grid > a").forEach((anchor) => {
        const small = anchor.querySelector("small")?.textContent.trim() || "";
        let district = anchor.dataset.district?.trim()
          || small.replace(subjectSuffix, "").trim();
        if (!district || district === province) {
          district = regionTitle.replace(new RegExp(`^${province}\\s*`), "").trim() || "주요 지역";
        }

        if (!regions.has(province)) regions.set(province, new Map());
        const districtMap = regions.get(province);
        if (!districtMap.has(district)) districtMap.set(district, []);
        districtMap.get(district).push(anchor);
        anchors.push(anchor);
        searchableByAnchor.set(anchor, normalizeSearch(
          `${province} ${district} ${anchor.textContent}`
        ).replace(/\s/g, ""));
      });
    });

    originalBlocks.forEach((block) => block.remove());
    Array.from(directory.children).forEach((child) => {
      if (child.classList.contains("directory-head")) return;
      if (!child.children.length && !child.textContent.trim()) child.remove();
    });

    const toolbar = document.createElement("div");
    toolbar.className = "directory-toolbar";
    toolbar.innerHTML = `
      <label class="directory-search">
        <span>지역·동네 이름으로 찾기</span>
        <input type="search" inputmode="search" autocomplete="off" placeholder="예: 서울 강동구, 명일동" aria-label="광역지역, 시군구 또는 동네 이름 검색">
      </label>
      <div class="directory-controls" aria-label="지역 목록 제어">
        <button type="button" data-directory-expand>모두 펼치기</button>
        <button type="button" data-directory-collapse>모두 접기</button>
        <button type="button" data-directory-reset aria-label="검색어를 지우고 전체 지역 목록 다시 보기">검색 초기화</button>
      </div>
      <p class="directory-result" role="status" aria-live="polite" aria-atomic="true">전체 ${anchors.length}개 동네</p>
    `;

    const provinceNav = document.createElement("nav");
    provinceNav.className = "province-nav";
    provinceNav.setAttribute("aria-label", "광역지역 빠른 선택");

    const provinceDirectory = document.createElement("div");
    provinceDirectory.className = "province-directory";

    const orderedProvinces = Array.from(regions.keys()).sort((a, b) => {
      const ai = provinceOrder.indexOf(a);
      const bi = provinceOrder.indexOf(b);
      return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
    });

    orderedProvinces.forEach((province, provinceIndex) => {
      const districtMap = regions.get(province);
      const count = Array.from(districtMap.values()).reduce((sum, list) => sum + list.length, 0);
      const provinceId = `province-${provinceIndex}`;

      const quickButton = document.createElement("button");
      quickButton.type = "button";
      quickButton.textContent = province;
      quickButton.dataset.target = provinceId;
      provinceNav.appendChild(quickButton);

      const provinceGroup = document.createElement("details");
      provinceGroup.className = "province-group";
      provinceGroup.id = provinceId;
      provinceGroup.dataset.province = province;
      provinceGroup.open = provinceIndex === 0;

      const summary = document.createElement("summary");
      summary.innerHTML = `
        <span><strong>${province}</strong><small>${districtMap.size}개 시군구</small></span>
        <em>${count}개 동네</em>
      `;
      provinceGroup.appendChild(summary);

      const districtStack = document.createElement("div");
      districtStack.className = "district-stack";

      districtMap.forEach((districtAnchors, district) => {
        const districtGroup = document.createElement("section");
        districtGroup.className = "district-group";
        districtGroup.dataset.district = district;

        const districtHead = document.createElement("div");
        districtHead.className = "district-head";
        districtHead.innerHTML = `<h3>${district}</h3><span>${districtAnchors.length}개</span>`;

        const buttonGrid = document.createElement("div");
        buttonGrid.className = "local-button-grid";
        districtAnchors.forEach((anchor) => buttonGrid.appendChild(anchor));

        districtGroup.append(districtHead, buttonGrid);
        districtStack.appendChild(districtGroup);
      });

      provinceGroup.appendChild(districtStack);
      provinceDirectory.appendChild(provinceGroup);
    });

    directory.querySelector(".directory-head")?.insertAdjacentElement("afterend", toolbar);
    toolbar.insertAdjacentElement("afterend", provinceNav);
    provinceNav.insertAdjacentElement("afterend", provinceDirectory);

    const provinceGroups = Array.from(provinceDirectory.querySelectorAll(".province-group"));
    const districtGroups = Array.from(provinceDirectory.querySelectorAll(".district-group"));
    const result = toolbar.querySelector(".directory-result");
    const input = toolbar.querySelector("input");

    const filterDirectory = () => {
      const keyword = normalizeSearch(input.value);
      const terms = keyword.split(" ").filter(Boolean);
      let matched = 0;

      districtGroups.forEach((districtGroup) => {
        let districtMatched = 0;
        districtGroup.querySelectorAll(".local-button-grid > a").forEach((anchor) => {
          const searchable = searchableByAnchor.get(anchor);
          const visible = terms.every((term) => searchable.includes(term));
          anchor.hidden = !visible;
          if (visible) {
            districtMatched += 1;
            matched += 1;
          }
        });
        districtGroup.hidden = districtMatched === 0;
        districtGroup.querySelector('.district-head span').textContent = `${districtMatched}개`;
      });

      provinceGroups.forEach((provinceGroup, provinceIndex) => {
        const visibleDistricts = provinceGroup.querySelectorAll(".district-group:not([hidden])").length;
        const visibleLocations = provinceGroup.querySelectorAll('.local-button-grid > a:not([hidden])').length;
        provinceGroup.querySelector('summary small').textContent = `${visibleDistricts}개 시군구`;
        provinceGroup.querySelector('summary em').textContent = `${keyword ? '검색 ' : ''}${visibleLocations}개 동네`;
        provinceGroup.hidden = visibleDistricts === 0;
        provinceGroup.open = keyword ? visibleDistricts > 0 : provinceIndex === 0;
      });

      result.textContent = keyword
        ? matched ? `${matched}개 동네를 찾았습니다.` : "검색 결과가 없습니다. 지역명을 바꾸거나 검색 초기화를 눌러 주세요."
        : `전체 ${anchors.length}개 동네`;
    };

    const resetSearch = () => {
      input.value = "";
      filterDirectory();
    };

    provinceNav.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-target]");
      if (!button) return;
      const target = provinceGroups.find((group) => group.id === button.dataset.target);
      if (!target) return;
      resetSearch();
      provinceGroups.forEach((group) => {
        group.open = group === target;
      });
      target.querySelector("summary")?.focus({ preventScroll: true });
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    });

    toolbar.querySelector("[data-directory-expand]").addEventListener("click", () => {
      provinceGroups.filter((group) => !group.hidden).forEach((group) => {
        group.open = true;
      });
    });

    toolbar.querySelector("[data-directory-collapse]").addEventListener("click", () => {
      provinceGroups.forEach((group) => {
        group.open = false;
      });
    });

    toolbar.querySelector("[data-directory-reset]").addEventListener("click", () => {
      resetSearch();
      input.focus({ preventScroll: true });
    });

    input.addEventListener("input", filterDirectory);
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      resetSearch();
    });
  });
})();
