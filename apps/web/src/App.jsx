import React, { useEffect, useMemo, useState } from 'react'

const Arrow = ({ left = false }) => (
  <svg viewBox="0 0 24 24" className={left ? 'arrow left' : 'arrow'} aria-hidden="true">
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
)

const Icon = ({ name }) => {
  const paths = {
    plus: <path d="M12 5v14M5 12h14" />,
    questions: <><path d="M5 5.5A2.5 2.5 0 0 1 7.5 3h9A2.5 2.5 0 0 1 19 5.5v7a2.5 2.5 0 0 1-2.5 2.5H11l-4.5 4v-4A2.5 2.5 0 0 1 4 12.5v-7Z" /><path d="M9 8h6M9 11h4" /></>,
    sources: <><path d="M6 4h10a2 2 0 0 1 2 2v14H8a2 2 0 0 1-2-2V4Z" /><path d="M8 17h10M9 8h6M9 11h6" /></>,
    cases: <><rect x="3" y="7" width="18" height="12" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18" /></>,
    saved: <path d="M6 4.5A1.5 1.5 0 0 1 7.5 3h9A1.5 1.5 0 0 1 18 4.5V21l-6-4-6 4Z" />,
    news: <><path d="M4 5h13v15H6a2 2 0 0 1-2-2V5Z" /><path d="M17 8h3v10a2 2 0 0 1-2 2M8 9h5M8 13h5M8 17h3" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    scales: <><path d="M12 4v16M8 20h8M5 7h14M7 7l-4 7h8L7 7ZM17 7l-4 7h8l-4-7Z" /></>,
    chevron: <path d="m9 6 6 6-6 6" />,
    send: <path d="m4 4 16 8-16 8 3-8-3-8Zm3 8h13" />,
  }
  return <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>
}

const versions = [
  {
    id: 'current', status: 'Գործող', tone: 'olive', from: '2021-05-01', to: null,
    range: '01.05.2021 — մինչ օրս',
    description: 'Գործատուի նախաձեռնությամբ պայմանագրի լուծման գործող հիմքերն ու երաշխիքները։',
    result: 'Ընտրված ամսաթվի դրությամբ կիրառելի է ՀՀ աշխատանքային օրենսգրքի 113-րդ հոդվածի գործող խմբագրությունը։',
  },
  {
    id: 'amended', status: 'Փոփոխված', tone: 'clay', from: '2019-02-12', to: '2021-04-30',
    range: '12.02.2019 — 30.04.2021',
    description: 'Այս ժամանակահատվածում գործել է նախորդ խմբագրությունը՝ այլ ծանուցման երաշխիքներով։',
    result: 'Ընտրված ամսաթիվը ներառվում է 2019 թվականի փոփոխված խմբագրության գործողության ժամանակահատվածում։',
  },
  {
    id: 'historical', status: 'Նախկին խմբագրություն', tone: 'gray', from: '2012-01-01', to: '2019-02-11',
    range: '01.01.2012 — 11.02.2019',
    description: 'Հոդվածի նախկին խմբագրությունը՝ մինչև 2019 թվականի օրենսդրական փոփոխությունը։',
    result: 'Ընտրված ամսաթվի համար կիրառելի է հոդված 113-ի նախկին խմբագրությունը։',
  },
]

const navItems = [
  ['questions', 'Հարցեր'], ['sources', 'Իրավական աղբյուրներ'], ['cases', 'Իմ գործերը'],
  ['saved', 'Պահվածները'], ['news', 'Նորություններ'], ['settings', 'Կարգավորումներ'],
]

function Logo({ onClick }) {
  const content = <><span className="brand-symbol"><i /><i /><i /></span><span>ARLIS <b>AI</b></span></>
  return onClick
    ? <button className="brand brand-home" onClick={onClick} aria-label="Վերադառնալ գլխավոր էջ">{content}</button>
    : <div className="brand">{content}</div>
}

function JusticeArtwork() {
  return <div className="justice-art" aria-hidden="true"><img src="/lady-justice.png" alt="" /></div>
}

function Sidebar({ onHome }) {
  return (
    <aside className="sidebar">
      <Logo onClick={onHome} />
      <button className="new-question"><Icon name="plus" />Նոր հարց</button>
      <nav>{navItems.map(([icon, label], index) => <button className={index === 0 ? 'active' : ''} key={label}><Icon name={icon} />{label}</button>)}</nav>
      <JusticeArtwork />
      <div className="profile"><span>ԱՄ</span><div><b>Անի Մարտիրոսյան</b><small>Անձնական հաշիվ</small></div><Icon name="chevron" /></div>
    </aside>
  )
}

function Progress({ stage }) {
  const steps = ['Հարցը վերլուծված է', 'Ժամանակի որոշում', 'Օրենսդրություն', 'Պատասխան']
  return <div className="progress">{steps.map((label, index) => <React.Fragment key={label}><div className={`progress-step ${index + 1 <= stage ? 'complete' : ''} ${index + 1 === stage ? 'active' : ''}`}><span>{String(index + 1).padStart(2, '0')}</span><p>{label}</p></div>{index < 3 && <i className={index + 1 < stage ? 'filled' : ''} />}</React.Fragment>)}</div>
}

function Calendar({ selected, onSelect }) {
  const [view, setView] = useState(() => new Date(selected.getFullYear(), selected.getMonth(), 1))
  const monthNames = ['Հունվար', 'Փետրվար', 'Մարտ', 'Ապրիլ', 'Մայիս', 'Հունիս', 'Հուլիս', 'Օգոստոս', 'Սեպտեմբեր', 'Հոկտեմբեր', 'Նոյեմբեր', 'Դեկտեմբեր']
  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: currentYear - 1990 }, (_, index) => currentYear - index)
  const daysInMonth = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate()
  const mondayStart = (new Date(view.getFullYear(), view.getMonth(), 1).getDay() + 6) % 7
  const cells = [...Array(mondayStart).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)]
  const changeMonth = (delta) => setView(new Date(view.getFullYear(), view.getMonth() + delta, 1))
  const sameMonth = selected.getFullYear() === view.getFullYear() && selected.getMonth() === view.getMonth()
  return (
    <div className="calendar">
      <header>
        <button onClick={() => changeMonth(-1)} aria-label="Նախորդ ամիս"><Icon name="chevron" /></button>
        <div className="calendar-selectors">
          <label><span className="sr-only">Ամիս</span><select value={view.getMonth()} onChange={event => setView(new Date(view.getFullYear(), Number(event.target.value), 1))}>{monthNames.map((month, index) => <option value={index} key={month}>{month}</option>)}</select></label>
          <label><span className="sr-only">Տարի</span><select value={view.getFullYear()} onChange={event => setView(new Date(Number(event.target.value), view.getMonth(), 1))}>{years.map(year => <option value={year} key={year}>{year}</option>)}</select></label>
        </div>
        <button onClick={() => changeMonth(1)} aria-label="Հաջորդ ամիս"><Icon name="chevron" /></button>
      </header>
      <div className="weekdays">{['Երկ', 'Երք', 'Չրք', 'Հնգ', 'Ուրբ', 'Շբթ', 'Կիր'].map(day => <span key={day}>{day}</span>)}</div>
      <div className="calendar-grid">{cells.map((day, index) => day ? <button key={`${view.getMonth()}-${day}`} className={sameMonth && selected.getDate() === day ? 'selected' : ''} onClick={() => onSelect(new Date(view.getFullYear(), view.getMonth(), day))}>{day}</button> : <span key={`empty-${index}`} />)}</div>
      <button className="calendar-today" onClick={() => { const today = new Date(); setView(new Date(today.getFullYear(), today.getMonth(), 1)); onSelect(today) }}>Այսօր</button>
    </div>
  )
}

function Timeline({ results = [], selectedIndex = 0, onSelect, loading }) {
  const selected = results[selectedIndex] || results[0]
  const excerpt = text => {
    const clean = String(text || '').replace(/\s+/g, ' ').trim()
    return clean.length > 190 ? `${clean.slice(0, 190)}…` : clean
  }
  return (
    <aside className="timeline-panel">
      <div className="chronos-art" aria-hidden="true"><img src="/chronos.png" alt="" /></div>
      <header>
        <div className="overline">Համապատասխան իրավական աղբյուրներ</div>
        <h2>{selected?.act_title || (loading ? 'Աղբյուրները որոնվում են…' : 'Իրավական աղբյուրներ')}</h2>
        <p>{selected?.article_number ? `Հոդված ${selected.article_number}` : results.length ? `${results.length} աղբյուր` : 'Արդյունքներ չկան'}</p>
      </header>
      <div className="timeline source-timeline" style={{ '--active-index': Math.max(selectedIndex, 0), '--source-count': Math.max(results.length, 1) }}>
        <div className="timeline-track"><span /></div>
        {results.map((result, index) => (
          <article
            key={`${result.source_url}-${result.article_number}-${index}`}
            className={`version ${index === 0 ? 'olive' : index === 1 ? 'clay' : 'gray'} ${index === selectedIndex ? 'selected' : ''}`}
            onClick={() => onSelect(index)} role="button" tabIndex="0"
            onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') onSelect(index) }}
          >
            <i className="node" />
            <div className="version-status">{result.act_type || 'Իրավական ակտ'}{index === selectedIndex && <span>Ընտրված աղբյուր</span>}</div>
            <time>{result.article_number ? `Հոդված ${result.article_number}` : 'Ընդհանուր դրույթ'} · {result.valid_from}{result.valid_to ? ` — ${result.valid_to}` : ' — գործող'}</time>
            <h3>{result.act_title}</h3><p>{excerpt(result.text)}</p>
            {result.source_url && <a href={result.source_url} target="_blank" rel="noreferrer" onClick={event => event.stopPropagation()}>Տեսնել ARLIS-ում ↗</a>}
          </article>
        ))}
      </div>
      {!!results.length && <div className="source-count">Պատասխանը հիմնված է {results.length} իրավական աղբյուրի վրա</div>}
    </aside>
  )
}

function formatDate(date) {
  return new Intl.DateTimeFormat('hy-AM', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(date)
}

function getVersion(date) {
  const iso = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  return versions.find(version => iso >= version.from && (!version.to || iso <= version.to)) || versions[versions.length - 1]
}

function resolveQuestionDate(text) {
  const today = new Date()
  if (/այսօր/i.test(text)) return today
  if (/երեկ/i.test(text)) return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1)
  const iso = text.match(/\b(\d{4})-(\d{1,2})-(\d{1,2})\b/)
  if (iso) return new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]))
  const numeric = text.match(/\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b/)
  if (numeric) return new Date(Number(numeric[3]), Number(numeric[2]) - 1, Number(numeric[1]))
  return null
}

function FrontPage({ onContinue }) {
  const [question, setQuestion] = useState('')
  const [needsDate, setNeedsDate] = useState(false)
  const [selectedDate, setSelectedDate] = useState(new Date())
  const submit = (event) => {
    event.preventDefault()
    if (!question.trim()) return
    const detected = resolveQuestionDate(question)
    if (detected) onContinue(question.trim(), detected)
    else setNeedsDate(true)
  }
  return (
    <main className={`front-page ${needsDate ? 'calendar-visible' : ''}`}>
      <header><Logo /></header>
      <section className="front-content">
        <div className="front-intro"><span>Հայաստանի իրավական օգնական</span><h1>Ի՞նչ իրավական հարց ունեք։</h1><p>Հարցրեք պարզ լեզվով։ Մենք կգտնենք հենց անհրաժեշտ ժամանակահատվածում գործող օրենսդրությունը։</p></div>
        <form className="front-question" onSubmit={submit}>
          <textarea value={question} onChange={event => { setQuestion(event.target.value); if (needsDate) setNeedsDate(false) }} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) submit(event) }} rows="3" placeholder="Գրեք ձեր հարցը…" autoFocus />
          <div><span>Enter՝ շարունակելու համար</span><button aria-label="Շարունակել"><Arrow /></button></div>
        </form>
        {needsDate && <section className="front-calendar">
          <div className="front-calendar-copy"><span>Ժամանակային ճշգրտում</span><h2>Ո՞ր ամսաթվին է վերաբերում հարցը։</h2><p>Հարցում ամսաթիվ չի նշվել։ Ընտրեք այն օրը, որի դրությամբ պետք է ստուգվի օրենսդրությունը։</p><div className="front-selected"><small>Ընտրված է</small><strong>{formatDate(selectedDate)}</strong><i><Icon name="check" /> Օրենսդրությունը կզտվի մինչև որոնումը</i></div></div>
          <div><Calendar selected={selectedDate} onSelect={setSelectedDate} /><button className="calendar-continue" onClick={() => onContinue(question.trim(), selectedDate)}>Շարունակել <Arrow /></button></div>
        </section>}
      </section>
      <footer>ARLIS AI · Պաշտոնական իրավական աղբյուրների հիման վրա</footer>
    </main>
  )
}

function ResearchWorkspace({ initialQuestion, initialDate, onBack }) {
  const [question, setQuestion] = useState(initialQuestion)
  const [draft, setDraft] = useState('')
  const [selectedDate, setSelectedDate] = useState(initialDate)
  const [stage, setStage] = useState(3)
  const [researchData, setResearchData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedSourceIndex, setSelectedSourceIndex] = useState(0)
  const chooseDate = (date) => { setSelectedDate(date); setStage(3) }
  const submit = (event) => { event.preventDefault(); if (!draft.trim()) return; setQuestion(draft.trim()); setDraft(''); setStage(2) }
  const targetDate = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(''); setResearchData(null); setSelectedSourceIndex(0)
    fetch('/api/research', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
      body: JSON.stringify({ question, target_date: targetDate, top_k: 5 }),
    }).then(async response => {
      if (!response.ok) throw new Error((await response.json()).detail || 'Որոնումը չհաջողվեց')
      return response.json()
    }).then(data => { setResearchData(data); setStage(3) }).catch(reason => {
      if (reason.name !== 'AbortError') setError(reason.message)
    }).finally(() => setLoading(false))
    return () => controller.abort()
  }, [question, targetDate])
  const topResult = researchData?.results?.[selectedSourceIndex] || researchData?.results?.[0]
  return (
    <main className="app-shell">
      <Sidebar onHome={onBack} />
      <section className="workspace">
        <button className="back" onClick={onBack}><Arrow left />Վերադառնալ հարցերին</button>
        <div className="question-label">Ձեր հարցը</div>
        <h1>{question}</h1>
        <Progress stage={stage} />
        <section className="temporal-section">
          <div className="section-intro"><span>Ժամանակային համատեքստ</span><h2>Ո՞ր ժամանակահատվածին է վերաբերում հարցը։</h2><p>Ընտրեք ամսաթիվը, որպեսզի գտնենք այդ օրը գործող օրենսդրությունը։</p></div>
          <div className="date-layout">
            <div className="selected-date"><span>Ընտրված ամսաթիվ</span><strong>{formatDate(selectedDate)}</strong><p><Icon name="check" /> Ամսաթիվը հաստատված է</p><small>Օրենսդրությունը կստուգվի հենց այս օրվա դրությամբ։</small></div>
            <div><Calendar selected={selectedDate} onSelect={chooseDate} /><p className="calendar-note"><Icon name="check" /> Ընտրված ամսաթվի դրությամբ կկիրառվի գործող օրենսդրությունը։</p></div>
          </div>
        </section>
        <section className={`legal-result ${stage === 4 ? 'answer-open' : ''} ${loading ? 'is-loading' : ''}`} key={`${targetDate}-${stage}`}>
          <Icon name="scales" /><div><span>{stage === 4 ? 'Պաշտոնական իրավական տեքստ' : 'Պարզեցված պատասխան'}</span>{loading ? <><h3>Պատրաստվում է աղբյուրներով հիմնավորված պատասխանը…</h3><p>Նախ զտվում և դասակարգվում են իրավական դրույթները, ապա պատասխանը կազմվում է միայն ընտրված աղբյուրներից։</p></> : error ? <><h3>Չհաջողվեց միանալ իրավական որոնման API-ին</h3><p>{error}</p></> : topResult ? stage === 4 ? <><h3>{topResult.act_title}{topResult.article_number ? ` · Հոդված ${topResult.article_number}` : ''}</h3><p>{topResult.text}</p><div className="live-meta"><span>{topResult.act_type || 'Իրավական ակտ'}</span><span>Ուժի մեջ՝ {topResult.valid_from}{topResult.valid_to ? ` — ${topResult.valid_to}` : ''}</span></div></> : <><h3>{researchData.simplified_answer ? 'Պատասխան՝ ըստ ընտրված ամսաթվի գործող աղբյուրների' : 'Պարզեցված պատասխանը հասանելի չէ'}</h3><p className="generated-answer">{researchData.simplified_answer || 'AI մոդելը պատասխան չի վերադարձրել։ Կարող եք բացել ամենահամապատասխան պաշտոնական դրույթը։'}</p><div className="answer-sources">Հիմնված է {researchData.source_count} իրավական աղբյուրի վրա</div><button onClick={() => setStage(4)}>Տեսնել հիմնական աղբյուրը <Arrow /></button></> : <><h3>Համապատասխան գործող դրույթ չի գտնվել</h3><p>Փորձեք վերաձևակերպել հարցը կամ ընտրել այլ ամսաթիվ։</p></>}</div>
        </section>
        {researchData?.answer_error && !researchData?.simplified_answer && <p className="generation-error">{researchData.answer_error}</p>}
        {researchData?.warning && <p className="dataset-warning">{researchData.warning}</p>}
        <form className="question-input" onSubmit={submit}><input value={draft} onChange={e => setDraft(e.target.value)} placeholder="Գրեք ձեր հարցը…" /><button aria-label="Ուղարկել"><Icon name="send" /></button></form>
      </section>
      <Timeline results={researchData?.results || []} selectedIndex={selectedSourceIndex} loading={loading} onSelect={index => { setSelectedSourceIndex(index); setStage(4) }} />
    </main>
  )
}

function App() {
  const [research, setResearch] = useState(null)
  if (!research) return <FrontPage onContinue={(question, date) => setResearch({ question, date })} />
  return <ResearchWorkspace initialQuestion={research.question} initialDate={research.date} onBack={() => setResearch(null)} />
}

export default App
