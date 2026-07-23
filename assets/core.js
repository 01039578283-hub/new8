(() => {
  const form = document.querySelector("[data-sms-form]");
  if (!form) return;

  const note = form.querySelector("[data-form-note]");

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!form.reportValidity()) return;

    const data = new FormData(form);
    const message = [
      "[코칭센터 학습상담 문의]",
      `학년: ${data.get("grade") || "미입력"}`,
      `과목: ${data.get("subject") || "미입력"}`,
      `현재 교재·진도: ${data.get("material") || "미입력"}`,
      `통화 가능 시간: ${data.get("time") || "미입력"}`,
      `상담 내용: ${data.get("concern") || "미입력"}`,
    ].join("\n");

    if (note) {
      note.textContent = "문자 앱을 여는 중입니다. 열리지 않으면 010-6839-8283으로 직접 문자해 주세요.";
    }

    window.location.href = `sms:01068398283?body=${encodeURIComponent(message)}`;
  });
})();
