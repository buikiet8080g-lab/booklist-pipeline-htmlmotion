// 片段 · 书单号引文（bl_quote）：一镜只放书中一段原文。
// 书单号的「信」在这句话上：观众要读得完、要看出这是书里的原话，不是旁白。所以：衬线体（NotoSerifSC，和正文思源黑拉开）、
// 大号引号压住左上、字号 88→40 自适应（按可用宽高取最大能放下 6 行的那一档）、出处/作者/页码分两段落定。
// cues：quote（一条，正文原文）· 可选 source（出处那一段的落定时刻；不写＝quote.at + 2.2）
//       data: { source:'《正面管教》', author:'简·尼尔森', page:'第 43 页', key:'被看见'（要划荧光笔的词，可选）, prefix:'· 第 3 章'（出处前的引子，可选） }
// 镜头：不漂不晃，只有「引号先落 → 正文逐行升起 → 关键词划线 → 出处落定」这一条时间线；全程 1.2% 的极缓推进，保证 t 是纯函数。
// spec.theme：底色 bg、正文 ink、出处 sub、引号和划线 accent；alpha 模式不画底，字走 ink + 深色描边。
CLIPS.bl_quote = (() => {
const { clamp, lerp } = U;
// 引文字体：LXGWWenKai-500（霞鹜文楷，OFL，GB2312 全字集）。上游的 NotoSerifSC-sub 只有示范片用到的字，
// 换成书里的真实句子就缺字、回退到系统黑体，正文和引文一眼分不开（2026-10 实测缺「孩爱候他」）。
const SERIF = 'LXGWWenKai-500', SANS = 'PuHui-Bold', SANSB = 'PuHui-Black';
const C0 = { bg: '#F3EDE2', ink: '#1B1A17', sub: '#6B655B', accent: '#C8402F', surface: '#FBF8F2' };
let Q = null, PALC = C0, T = null;
return {
  fonts: ['LXGWWenKai-500', 'PuHui-Bold'],
  kinds: ['quote', 'source'],                                                  // cue 白名单（clip.js 校验，见 patches/0006）
  safe: true,
  init(ctx) {
    const { W, H, u, safe } = ctx, bx = ctx.box;
    const left = Math.max(bx.x, 56);                 // 左安全边 48px：出处不贴画布边（实测 29px 起笔被 lint 判进安全区）
    const q = ctx.of('quote')[0];
    PALC = ctx.pal ? { bg: ctx.pal.bg, ink: ctx.pal.ink, sub: ctx.pal.sub, accent: ctx.pal.accent, surface: ctx.pal.surface } : C0;
    T = { bg: PALC.bg, ink: PALC.ink, sub: PALC.sub, acc: PALC.accent };
    if (!q || !String(q.text || '').trim()) { Q = null; console.warn('bl_quote：没有 quote cue（或 text 为空），这一镜只剩底色'); return; }
    const d = q.data || {}, g = document.createElement('canvas').getContext('2d');
    const bandH = bx.h, markH = (ctx.portrait ? 150 : 120) * u, srcH = (ctx.portrait ? 150 : 120) * u;
    const maxW = bx.w - left - (ctx.portrait ? 150 : 220) * u - (ctx.portrait ? 70 : 100) * u,   // 左边留给大引号，右边留出呼吸；右边不扣这一块会顶到画布边缘（实测字被画布切掉）
          maxH = bandH - markH - srcH - 60 * u;
    // 字号自适应：从 88px（屏幕上）往下试，直到折行 ≤6 行且总高放得下；最小 40px（再小就读不动了）
    const base = ctx.portrait ? 88 : 76;
    let size = base, f;
    for (; size >= 40; size -= 4) {
      f = TY.fit(g, q.text, maxW, size, SERIF, { maxLines: 6, min: 0.2, balance: true });
      if (f.ok && f.lines.length * f.size * 1.5 <= maxH) break;
    }
    const lh = f.size * 1.5, blkH = f.lines.length * lh;
    const y0 = bx.y + markH + Math.max(0, (maxH - blkH) / 2) + f.size * 0.9;   // 正文块在引号下方居中
    const srcAt = (ctx.of('source')[0] && ctx.of('source')[0].at) || (q.at + 2.2);
    Q = { q, d, f, size: f.size, lh, y0, x: left + (ctx.portrait ? 150 : 190) * u, maxW,
      srcY: Math.min(bx.y + bx.h - 40 * u, y0 + blkH + (ctx.portrait ? 120 : 96) * u),
      markX: left, markY: bx.y + markH * 0.92, markSz: markH * 0.95,
      at: q.at, srcAt, src: d.source || '', author: d.author || '', page: d.page || '', prefix: d.prefix || '', key: d.key || '' };
  },
  draw(c, t, ctx) {
    const { W, H, u } = ctx;
    if (!ctx.alpha) {
      c.fillStyle = T.bg; c.fillRect(0, 0, W, H);
      // 纸纹：两条极淡的竖线＋顶部一道 accent 细线，让画面不是纯色块（不是风格配方，纯 token 派生）
      c.save(); c.globalAlpha = 0.06; c.fillStyle = T.ink;
      for (let i = 0; i < 2; i++) c.fillRect(ctx.box.x + (i + 1) * ctx.box.w / 3, ctx.box.y + 20 * u, 1.5 * u, ctx.box.h - 40 * u);
      c.restore();
      c.save(); c.globalAlpha = 0.9; c.fillStyle = T.acc; c.fillRect(ctx.box.x, ctx.safe.top + 8 * u, 96 * u, 8 * u); c.restore();
    }
    if (!Q) return;
    const pl = ctx.p(t, Q.at - 0.15, 0.55), push = 1 + 0.012 * clamp((t - Q.at) / ctx.dur);   // 极缓推进：只做微动，不做运镜
    c.save(); c.translate(W / 2, H / 2); c.scale(push, push); c.translate(-W / 2, -H / 2);
    const stroke = ctx.alpha ? { stroke: '#111', strokeW: Q.size * 0.05 } : {};
    // 大引号：一拍砸入（MO.slamK），落定后不动
    const mk = MO.slamK(clamp(ctx.lt(t, Q.at - 0.15) / 0.42), 1.25, 0.96);
    c.save(); c.translate(Q.markX + Q.markSz * 0.3, Q.markY - Q.markSz * 0.42); c.scale(mk, mk); c.translate(-(Q.markX + Q.markSz * 0.3), -(Q.markY - Q.markSz * 0.42));
    c.globalAlpha = clamp(pl * 2); TY.text(c, '「', Q.markX, Q.markY, { size: Q.markSz, fam: SERIF, color: T.acc, align: 'left', ...(ctx.alpha ? { stroke: '#111', strokeW: Q.markSz * 0.05 } : {}) });
    c.restore();
    // 关键词荧光笔先铺（画在字下面，35% 透明，字不会被涂掉），再逐行升起正文（每行 +0.09s）
    if (Q.key) {
      const hp = ctx.p(t, Q.at + 0.9, 0.5);
      // 关键词可能正好被折行切开（「不可爱」→「不可」/「爱」）：按每行能匹配到的最长片段划（≥2 字），跨行也划得出来
      const seg = ln => { let best = ''; for (let i = 0; i < Q.key.length; i++) for (let j = i + 2; j <= Q.key.length; j++) { const sub = Q.key.slice(i, j); if (ln.includes(sub) && sub.length > best.length) best = sub; } return best; };
      Q.f.lines.forEach((ln, i) => {
        const w0 = seg(ln); if (!w0) return;
        const at = ln.indexOf(w0);
        const wPre = TY.width(c, ln.slice(0, at), Q.size, SERIF), wKey = TY.width(c, w0, Q.size, SERIF);
        c.save(); c.globalAlpha = 0.32; TY.marker(c, Q.x + wPre - 8 * u, Q.y0 + i * Q.lh - Q.size * 0.9, (wKey + 16 * u) * clamp(hp), Q.size * 1.1, 1, T.acc); c.restore();
      });
    }
    Q.f.lines.forEach((ln, i) => {
      const p = ctx.p(t, Q.at + i * 0.09, 0.4);
      TY.rise(c, ln, Q.x, Q.y0 + i * Q.lh, p, { size: Q.size, fam: SERIF, color: T.ink, align: 'left', ...stroke });
    });
    // 出处：prefix · 《书名》 · 作者 · 页码，一行放不下就缩到放得下（不截断）
    // 出处分两段：书名一段、作者与页码一段；中间用真实换行，折行不会把「岸见一郎」拆成「岸见一/郎」
    const l1 = [Q.prefix, Q.src].filter(Boolean).join(' · '), l2 = [Q.author, Q.page].filter(Boolean).join(' · ');
    const bits = [l1, l2].filter(Boolean).join(l1 && l2 && (l1 + l2).length > 14 ? '\n' : ' · ');
    if (bits) {
      const sp = ctx.p(t, Q.srcAt, 0.45);
      // 出处字号用屏幕 px（不乘 u：u=0.667 时 40u 只有 27px，低于 32px 下限）；放不下折两行，不再缩到看不清
      const sf = TY.fit(c, bits, Math.min(ctx.box.w - Q.markX - 80 * u, ctx.box.w - 48 - 40 * u), ctx.portrait ? 34 : 32, SANS, { maxLines: 2, min: 0.85, balance: true });
      // 出处前一道短线，跟着文字一起长出来
      c.save(); c.globalAlpha = clamp(sp) * 0.9; c.fillStyle = T.acc; c.fillRect(Q.markX, Q.srcY - sf.size * 0.34, 56 * u * clamp(sp), 3 * u); c.restore();
      sf.lines.forEach((ln, k) => TY.rise(c, ln, Q.markX, Q.srcY + k * sf.size * 1.35, sp, { size: sf.size, fam: SANS, color: T.sub, align: 'left', ...(ctx.alpha ? { stroke: '#111', strokeW: sf.size * 0.06 } : {}) }));
    }
    c.restore();
  },
};
})();
