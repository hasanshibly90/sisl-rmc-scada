cd apps\api\frontend
npm install
npm run dev 2>&1 | Tee-Object -FilePath "..\..\..\logs_frontend.txt"
