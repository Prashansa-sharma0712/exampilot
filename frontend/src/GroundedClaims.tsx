import type { ReactNode } from 'react'
import type { Answer } from './api'

export default function GroundedClaims({answer,citation}:{answer:Answer;citation:(id:string)=>ReactNode}){
  const note=answer.study_note||'Source wording is shown directly. Check its citation for context.'
  if(!answer.claims.length)return <p className="refusal">{answer.answer}</p>
  return <><p className="study-note">{note}</p>{answer.study_format==='compare'?<div className="comparison-scroll"><table className="comparison-table"><thead><tr><th>Requested part</th><th>What the material supports</th></tr></thead><tbody>{answer.coverage.map((need,i)=><tr key={i}><th>{need.need}</th><td>{need.supported?answer.claims.filter(c=>c.citations.some(id=>need.citations.includes(id))).map((c,n)=><div className="claim" key={n}><p>{c.text}</p><div className="citations">{c.citations.map(citation)}</div></div>):<span className="missing">Not found in the available evidence.</span>}</td></tr>)}</tbody></table></div>:<div className={answer.study_format==='exam'?'exam-outline':answer.study_format==='simple'?'simple-view':''}>{answer.claims.map((claim,n)=><div className="claim" key={n}>{answer.study_format==='exam'&&<span className="outline-number">Point {n+1}</span>}<p>{claim.text}</p><div className="citations">{claim.citations.map(citation)}</div></div>)}</div>}</>
}
