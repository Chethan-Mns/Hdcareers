import {put} from "@vercel/blob";
import {readFile} from "node:fs/promises";
import path from "node:path";
const filename=process.argv[2];
if(!filename||!process.env.BLOB_READ_WRITE_TOKEN)throw new Error("Reel file and BLOB_READ_WRITE_TOKEN required");
const bytes=await readFile(filename);
if(bytes.length<10000)throw new Error("Reel MP4 unexpectedly small");
const uploaded=await put("hd-reels/"+new Date().toISOString().slice(0,10)+"-"+path.basename(filename),bytes,
  {access:"public",token:process.env.BLOB_READ_WRITE_TOKEN,addRandomSuffix:true,contentType:"video/mp4"});
if(!/^https:\/\//.test(uploaded.url))throw new Error("Invalid public video URL");
process.stdout.write(uploaded.url+"\n");
