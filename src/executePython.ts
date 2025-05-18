import axios from 'axios'

export async function executePython(code: string, input: string) {
  const res = await axios.post('/api/execute', { code, input })
  return res.data
}
