(() => {
  const provinceOrder = [
    "서울", "경기", "인천", "충청", "대전", "세종", "대구",
    "울산", "부산", "경상", "광주", "전라", "강원", "제주"
  ];
  const subjectSuffix = /\s+(?:고등(?:수학|영어|영수)|국영수).*$/;

  document.querySelectorAll(".directory-page .academy-directory").forEach((directory) => {
    const originalBlocks = Array.from(directory.querySelectorAll(".region-block"));
    if (!originalBlocks.length) return;

    const regions = new Map();
    const anchors = [];

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
        <span>동네 이름으로 찾기</span>
        <input type="search" inputmode="search" autocomplete="off" placeholder="예: 명일동, 불당동, 중계동" aria-label="동네 이름 검색">
      </label>
      <div class="directory-controls" aria-label="지역 목록 제어">
        <button type="button" data-directory-expand>모두 펼치기</button>
        <button type="button" data-directory-collapse>모두 접기</button>
      </div>
      <p class="directory-result" aria-live="polite">전체 ${anchors.length}개 동네</p>
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

    provinceNav.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-target]");
      if (!button) return;
      const target = document.getElementById(button.dataset.target);
      if (!target) return;
      target.hidden = false;
      target.open = true;
      target.scrollIntoView({ behavior: "smooth", block: "start" });
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

    input.addEventListener("input", () => {
      const keyword = input.value.trim().toLocaleLowerCase("ko-KR");
      let matched = 0;

      districtGroups.forEach((districtGroup) => {
        let districtMatched = 0;
        districtGroup.querySelectorAll(".local-button-grid > a").forEach((anchor) => {
          const searchable = `${anchor.textContent} ${districtGroup.dataset.district}`.toLocaleLowerCase("ko-KR");
          const visible = !keyword || searchable.includes(keyword);
          anchor.hidden = !visible;
          if (visible) {
            districtMatched += 1;
            matched += 1;
          }
        });
        districtGroup.hidden = districtMatched === 0;
      });

      provinceGroups.forEach((provinceGroup) => {
        const visibleDistricts = provinceGroup.querySelectorAll(".district-group:not([hidden])").length;
        provinceGroup.hidden = visibleDistricts === 0;
        if (keyword && visibleDistricts) provinceGroup.open = true;
      });

      result.textContent = keyword
        ? `${matched}개 동네를 찾았습니다.`
        : `전체 ${anchors.length}개 동네`;
    });
  });
})();
