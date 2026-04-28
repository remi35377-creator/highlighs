$body = '{"email":"remi35377@gmail.com","code":"168594","verify_token":"{\"email\": \"remi35377@gmail.com\", \"code\": \"168594\", \"exp\": 1777408279.641422}.a80a2ef85ec0fb927eb45268a3eb2363d1fe1961828eb58023dc49084015cde0"}'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
$req = [System.Net.WebRequest]::Create('https://highlighs.vercel.app/api/auth/verify')
$req.Method = 'POST'
$req.ContentType = 'application/json'
$req.ContentLength = $bytes.Length
$req.GetRequestStream().Write($bytes, 0, $bytes.Length)
$resp = $req.GetResponse()
$reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
Write-Host "Response:" $reader.ReadToEnd()