export async function onRequestGet({ request }) {
  const url = new URL(request.url);
  const filename = url.searchParams.get("file");

  if (!filename) {
    return new Response("Missing file parameter", { status: 400 });
  }

  // Security: block path traversal
  if (/[\/\]/.test(filename)) {
    return new Response("Invalid filename", { status: 400 });
  }

  const fileUrl = new URL(filename, url.origin).toString();

  try {
    const fileResponse = await fetch(fileUrl, {
      cf: { cacheEverything: true },
    });

    if (!fileResponse.ok) {
      return new Response("File not found", { status: 404 });
    }

    // Clone headers and force download
    const headers = new Headers(fileResponse.headers);
    headers.set("Content-Disposition", "attachment; filename*=UTF-8''" + encodeURIComponent(filename));

    return new Response(fileResponse.body, {
      status: fileResponse.status,
      headers: headers,
    });
  } catch (e) {
    return new Response("Error: " + e.message, { status: 500 });
  }
}
