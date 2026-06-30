export function iconSvg(name: string): string {
  const paths: Record<string, string> = {
    Play: '<polygon points="8 5 19 12 8 19 8 5"></polygon>',
    User: '<path d="M20 21a8 8 0 0 0-16 0"></path><circle cx="12" cy="7" r="4"></circle>',
    Inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"></path><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6l3.5-7Z"></path>',
    List: '<path d="M8 6h13"></path><path d="M8 12h13"></path><path d="M8 18h13"></path><path d="M3 6h.01"></path><path d="M3 12h.01"></path><path d="M3 18h.01"></path>',
    Library: '<path d="M4 19.5V5a2 2 0 0 1 2-2h12"></path><path d="M6 17h14"></path><path d="M6 22h14"></path><path d="M6 17a2 2 0 1 0 0 4"></path>',
    FileText: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"></path><path d="M14 2v6h6"></path><path d="M16 13H8"></path><path d="M16 17H8"></path><path d="M10 9H8"></path>',
    Gear: '<path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z"></path><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.04.04a2 2 0 1 1-2.83 2.83l-.04-.04A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21a2 2 0 1 1-4 0v-.06A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.04.04a2 2 0 1 1-2.83-2.83l.04-.04A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.6-1H3a2 2 0 1 1 0-4h.06A1.7 1.7 0 0 0 4.6 8.6a1.7 1.7 0 0 0-.34-1.88l-.04-.04a2 2 0 1 1 2.83-2.83l.04.04A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3a2 2 0 1 1 4 0v.06A1.7 1.7 0 0 0 15.4 4.6a1.7 1.7 0 0 0 1.88-.34l.04-.04a2 2 0 1 1 2.83 2.83l-.04.04A1.7 1.7 0 0 0 19.4 9c.16.58.62 1 1.2 1H21a2 2 0 1 1 0 4h-.06a1.7 1.7 0 0 0-1.54 1Z"></path>',
    Wrench: '<path d="M14.7 6.3a4 4 0 0 0-5 5L3 18l3 3 6.7-6.7a4 4 0 0 0 5-5l-2.8 2.8-2-2 2.8-2.8Z"></path>',
    Route: '<circle cx="6" cy="19" r="3"></circle><circle cx="18" cy="5" r="3"></circle><path d="M9 19h1.5a3.5 3.5 0 0 0 0-7H9.5a3.5 3.5 0 0 1 0-7H15"></path>',
    Terminal: '<path d="m4 17 6-6-6-6"></path><path d="M12 19h8"></path>',
    Upload: '<path d="M12 3v12"></path><path d="m17 8-5-5-5 5"></path><path d="M21 21H3"></path>',
    Sliders: '<path d="M4 21v-7"></path><path d="M4 10V3"></path><path d="M12 21v-9"></path><path d="M12 8V3"></path><path d="M20 21v-5"></path><path d="M20 12V3"></path><path d="M2 14h4"></path><path d="M10 8h4"></path><path d="M18 16h4"></path>',
  };
  return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] ?? ""}</svg>`;
}

export function field(label: string, id: string, value: string, type = "text"): string {
  return `<label class="field"><span>${escapeHtml(label)}</span><input id="${id}" type="${type}" value="${escapeAttr(value)}" /></label>`;
}

export function pathField(label: string, id: string, value: string, disabled = false): string {
  const disabledAttr = disabled ? "disabled" : "";
  return `<label class="field path-field"><span>${escapeHtml(label)}</span><div class="path-input"><input id="${id}" type="text" value="${escapeAttr(value)}" /><button type="button" data-choose-directory="${escapeAttr(id)}" ${disabledAttr}>选择</button></div></label>`;
}

export function checkbox(label: string, id: string, checkedValue: boolean): string {
  return `<label class="field check"><input id="${id}" type="checkbox" ${checkedValue ? "checked" : ""} /><span>${escapeHtml(label)}</span></label>`;
}

export function selectField(label: string, id: string, options: Array<[string, string]>, selected = ""): string {
  return `<label class="field"><span>${escapeHtml(label)}</span><select id="${id}">
    ${options.map(([value, text]) => `<option value="${escapeAttr(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(text)}</option>`).join("")}
  </select></label>`;
}

export function hidden(id: string, value: string): string {
  return `<input id="${id}" type="hidden" value="${escapeAttr(value)}" />`;
}

export function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char] ?? char;
  });
}

export function escapeAttr(value: string): string {
  return escapeHtml(value);
}
