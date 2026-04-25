$body = '{"email":"test@example.com"}'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
$req = [System.Net.WebRequest]::Create('https://highlighs.vercel.app/api/auth/send-code')
$req.Method = 'POST'
$req.ContentType = 'application/json'
$req.ContentLength = $bytes.Length
$req.GetRequestStream().Write($bytes, 0, $bytes.Length)
$resp = $req.GetResponse()
$reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
$reader.ReadToEnd()