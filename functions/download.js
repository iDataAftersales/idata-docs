export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const filename = url.searchParams.get('file');

  if (!filename) {
    return new Response('Missing file parameter', { status: 400 });
  }

  // Security: only allow safe characters in filename
  if (/[\/\\]/.test(filename)) {
    return new Response('Invalid filename', { status: 400 });
  }

  // Fetch the file from Cloudflare Pages assets
  const fileUrl = new URL(filename, url.origin).toString();

  try {
    const fileResponse = await fetch(fileUrl, { cf: { cacheEverything: true } });

    if (!fileResponse.ok) {
      return new Response('File not found', { status: 404 });
    }

    // Clone and add Content-Disposition to force download
    const headers = new Headers(fileResponse.headers);
    headers.set('Content-Disposition', `attachment; filename*=UTF-8''${encodeURIComponent(filename)}`);

    return new Response(fileResponse.body, {
      status: fileResponse.status,
      headers: headers,
    });
  } catch (e) {
    return new Response('Error: ' + e.message, { status: 500 });
  }
}
