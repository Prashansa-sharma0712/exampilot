export type Source = {chunk_id:string;document_id:string;document_name:string;source_type:string;page:number|null;slide:number|null;section:string|null;location:string;text:string;extraction_quality:string;extraction_method:string;preview_url:string;original_url:string}
export type Answer = {status:string;answer:string;claims:{text:string;citations:string[];quotes:Record<string,string>}[];coverage:{need:string;supported:boolean;citations:string[]}[];missing_evidence:string[];sources:Source[];session_id:string;resolved_question:string;mode:string;warnings:string[];retrieval_ms:number;query_intent:string;study_format:string;study_note:string}
export type Document = {id:string;name:string;source_type:string;units:number;chunks:number;low_quality:number}
export type Topic = {topic:string;status:string;asked:number;correct:number;total:number}
export type Sprint = {topics:Topic[];weak:Topic[];strong:Topic[];saved:Answer[];quiz_correct:number;quiz_total:number;recommended:Topic|null;coverage_note:string}
export type Message = {question:string;answer:Answer;created:string}
export async function api<T>(path:string, body?:unknown):Promise<T>{
  const response = await fetch('/api'+path,body === undefined ? undefined : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
  if(!response.ok){const error=await response.json().catch(()=>({detail:'The server could not complete this request.'}));throw new Error(typeof error.detail==='string'?error.detail:'Please check your input and try again.')}
  return response.json() as Promise<T>
}
