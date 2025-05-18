import axios from 'axios'

export async function executePython(code: string, input: string) {
  // Use localhost for local development. Change to your VPS IP/domain when deploying.
  const backendUrl = 'http://localhost:8000/execute'; // e.g., http://your-vps-ip:8000/execute
  const res = await axios.post(backendUrl, { code, input });
  return res.data;
}