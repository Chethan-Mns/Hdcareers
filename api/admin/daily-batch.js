import {requireAdmin} from "../../lib/admin-auth.js";

const REPO = process.env.ADMIN_GITHUB_REPO || "Chethan-Mns/Hdcareers";
const REF = process.env.ADMIN_GITHUB_BASE || "main";
const PATH = "data/daily-review-batch.json";

function originAllowed(req) {
  const origin = String(req.headers.origin || "");
  if (!origin) return true;
  const host = String(req.headers["x-forwarded-host"] || req.headers.host || "").toLowerCase();
  try { return new URL(origin).host.toLowerCase() === host; } catch { return false; }
}

async function github(path, token, options = {}) {
  const response = await fetch("https://api.github.com/repos/" + REPO + path, {
    ...options,
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: "Bearer " + token,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "HD-Careers-Daily-Review",
      ...(options.headers || {})
    }
  });
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = {message: text}; }
  if (!response.ok) {
    const error = new Error(data.message || "GitHub returned HTTP " + response.status);
    error.status = response.status;
    throw error;
  }
  return data;
}

function blank() {
  return {batchId: "", generatedAt: null, status: "waiting", priority: [], backup: [], updatedAt: null};
}

async function read(token) {
  try {
    const file = await github("/contents/" + PATH + "?ref=" + encodeURIComponent(REF), token);
    const data = JSON.parse(Buffer.from(String(file.content || "").replace(/\n/g, ""), "base64").toString("utf8"));
    return {data, sha: file.sha};
  } catch (error) {
    if (error.status === 404) return {data: blank(), sha: null};
    throw error;
  }
}

function category(candidate) {
  const category = String(candidate?.cat || candidate?.job?.cat || "it").toLowerCase();
  if (category === "nonit") return "nonit";
  if (category === "internship" || category === "apprenticeship") return "training";
  return "it";
}

function company(candidate) {
  return String(candidate?.company || candidate?.job?.company || "").trim().toLowerCase();
}

function update(data, body) {
  const action = String(body?.action || "");
  if (data.status === "submitted" || data.status === "published") {
    throw Object.assign(new Error("This batch has already been submitted. Refresh to get the latest status."), {status: 409});
  }
  if (!Array.isArray(data.priority) || !Array.isArray(data.backup)) throw new Error("Invalid review batch.");
  const all = [...data.priority, ...data.backup];
  if (action === "review") {
    const item = all.find(x => String(x.id) === String(body.candidateId));
    if (!item) throw Object.assign(new Error("Job not found in this batch."), {status: 404});
    const decision = String(body.decision || "").toLowerCase();
    if (!["live", "expired", "unsure"].includes(decision)) {
      throw Object.assign(new Error("Choose Live, Expired or Unsure."), {status: 400});
    }
    item.reviewedStatus = decision;
    item.reviewedAt = new Date().toISOString();
    item.reviewedBy = "HD Careers Admin";
  } else if (action === "swap") {
    const pi = data.priority.findIndex(x => String(x.id) === String(body.priorityId));
    const bi = data.backup.findIndex(x => String(x.id) === String(body.backupId));
    if (pi < 0 || bi < 0) throw Object.assign(new Error("Choose a priority and backup job."), {status: 404});
    const outgoing = data.priority[pi], incoming = data.backup[bi];
    if (incoming.reviewedStatus !== "live") {
      throw Object.assign(new Error("Verify the backup job as Live before replacing."), {status: 400});
    }
    if (category(outgoing) !== category(incoming)) {
      throw Object.assign(new Error("Choose a backup from the same IT, Non-IT or Internship category."), {status: 400});
    }
    if (data.priority.some((j, index) => index !== pi && company(j) === company(incoming))) {
      throw Object.assign(new Error("Priority jobs must come from different employers."), {status: 409});
    }
    data.priority[pi] = incoming;
    data.backup[bi] = outgoing;
  } else if (action === "submitted") {
    if (data.priority.length !== 10 || data.priority.some(x => x.reviewedStatus !== "live")) {
      throw Object.assign(new Error("Ten priority jobs must be reviewed Live before submission."), {status: 400});
    }
    data.status = "submitted";
    data.submittedAt = new Date().toISOString();
  } else {
    throw Object.assign(new Error("Invalid review action."), {status: 400});
  }
  data.updatedAt = new Date().toISOString();
  return data;
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "private, no-store");
  if (!["GET", "POST"].includes(req.method)) {
    res.setHeader("Allow", "GET, POST");
    return res.status(405).json({error: "Method not allowed."});
  }
  if (!requireAdmin(req, res)) return;
  if (!originAllowed(req)) return res.status(403).json({error: "Invalid request origin."});
  const token = process.env.GITHUB_PUBLISH_TOKEN;
  if (!token) return res.status(503).json({error: "GitHub publishing credentials are not configured."});
  try {
    if (req.method === "GET") return res.status(200).json((await read(token)).data);
    for (let attempt = 0; attempt < 3; attempt++) {
      const {data, sha} = await read(token);
      if (req.body?.batchId !== data.batchId || !data.batchId) {
        return res.status(409).json({error: "Review batch changed. Refresh and try again."});
      }
      const next = update(data, req.body);
      try {
        await github("/contents/" + PATH, token, {
          method: "PUT",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            message: "Admin review: " + String(req.body?.action || "update"),
            content: Buffer.from(JSON.stringify(next, null, 2) + "\n").toString("base64"),
            sha,
            branch: REF
          })
        });
        return res.status(200).json(next);
      } catch (error) {
        if (![409, 422].includes(error.status) || attempt === 2) throw error;
      }
    }
  } catch (error) {
    return res.status(error.status >= 400 && error.status < 500 ? error.status : 502).json({
      error: error.message || "Could not save review decision."
    });
  }
}