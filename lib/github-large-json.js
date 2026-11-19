/**
 * GitHub Contents API deliberately omits inline content for files >1 MiB:
 * {encoding:"none", content:"", sha:"..."}.
 * Fetch the matching Git Blob by SHA instead of parsing an empty string.
 * Works for smaller files too; callers keep the same exact ref/commit.
 */
export async function decodeGitHubJSON(file, fetchBlob, label="GitHub JSON file"){
  if(!file || typeof file!=="object")throw new Error(label+": GitHub file metadata is missing.");
  let source=file;
  if(source.encoding==="none" || !String(source.content||"").trim()){
    if(!source.sha || typeof fetchBlob!=="function")
      throw new Error(label+": GitHub omitted the contents and no blob reader is available.");
    source=await fetchBlob(source.sha);
  }
  if(source?.encoding!=="base64" || !String(source.content||"").trim())
    throw new Error(label+": GitHub returned no readable file contents.");
  const raw=Buffer.from(String(source.content).replace(/\s/g,""),"base64").toString("utf8");
  if(!raw.trim())throw new Error(label+": GitHub returned empty file contents.");
  try{return JSON.parse(raw);}
  catch{throw new Error(label+": GitHub returned invalid or incomplete JSON; publishing was not started.");}
}
