import type { NextApiRequest, NextApiResponse } from 'next'
import { spawn } from 'child_process'

export const config = {
  api: {
    bodyParser: true,
    responseLimit: '2mb',
    externalResolver: true,
  },
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }
  const { code, input } = req.body
  if (typeof code !== 'string') {
    res.status(400).json({ error: 'Missing code' })
    return
  }
  try {
    const py = spawn('python3', ['-u', '-c', code])
    let stdout = ''
    let stderr = ''
    if (typeof input === 'string' && input.length > 0) {
      py.stdin.write(input + '\n')
    }
    py.stdin.end()
    py.stdout.on('data', (data) => { stdout += data.toString() })
    py.stderr.on('data', (data) => { stderr += data.toString() })
    py.on('close', (exitCode) => {
      res.status(200).json({ stdout, stderr, exitCode })
    })
  } catch (e) {
    res.status(500).json({ error: 'Execution error', details: String(e) })
  }
}
