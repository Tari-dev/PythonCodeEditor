import { useRef, useEffect, useState } from 'react'
import Editor from '@monaco-editor/react'
import { Terminal } from 'xterm'
import 'xterm/css/xterm.css'
import './App.css'
import { executePythonWS } from './executePython'

const DEFAULT_CODE = `print('Hello, young coder!')\nname = input('What is your name? ')
print('Nice to meet you,', name)`

function App() {
  const [isRunning, setIsRunning] = useState(false)
  const [files, setFiles] = useState([
    { name: 'main.py', content: DEFAULT_CODE }
  ])
  const [activeFile, setActiveFile] = useState('main.py')
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<Terminal | null>(null)

  useEffect(() => {
    if (terminalRef.current && !xtermRef.current) {
      xtermRef.current = new Terminal({
        fontSize: 16,
        theme: { background: '#1a1a1a' },
        cursorBlink: true,
        cursorStyle: 'bar',
        cursorWidth: 1,
      })
      xtermRef.current.open(terminalRef.current)
      // Reset scroll to left after each clear
      xtermRef.current.onRender(() => {
        if (terminalRef.current) {
          terminalRef.current.scrollLeft = 0;
        }
      })
    }
  }, [])

  // Interactive code execution using WebSocket
  const runCode = () => {
    setIsRunning(true)
    xtermRef.current?.clear()
    let sendInput: ((input: string) => void) | null = null
    sendInput = executePythonWS(currentFile.content, {
      onStdout: (data) => {
        xtermRef.current?.write(data)
        // After each line, reset cursor to column 0
        if (data.endsWith('\n')) {
          xtermRef.current?.write('\r')
        }
      },
      onStderr: (data) => {
        xtermRef.current?.write(data)
        if (data.endsWith('\n')) {
          xtermRef.current?.write('\r')
        }
      },
      onClose: () => setIsRunning(false),
    })
    // Listen for terminal key events and send to backend
    if (xtermRef.current && sendInput) {
      xtermRef.current.focus()
      // Remove previous key listeners to avoid duplicates
      if ((xtermRef.current as any)._keyListenerDispose) {
        ((xtermRef.current as any)._keyListenerDispose as { dispose: () => void }).dispose();
      }
      // Add new key listener and store dispose function
      const keyListenerDispose: { dispose: () => void } = xtermRef.current.onKey((e) => {
        if (e.domEvent.key === 'Enter') {
          sendInput('\n');
        } else if (e.domEvent.key.length === 1) {
          sendInput(e.domEvent.key);
        } else if (e.domEvent.key === 'Backspace') {
          sendInput('\b');
        }
      });
      (xtermRef.current as any)._keyListenerDispose = keyListenerDispose;
    }
  }

  // Share code (placeholder)
  const shareCode = () => {
    window.alert('Shareable link feature coming soon!')
  }

  // Show code snippets (placeholder)
  const showSnippets = () => {
    window.alert('Code snippets for learning coming soon!')
  }

  const handleAddFile = () => {
    let i = 1
    let newName = `file${i}.py`
    while (files.some(f => f.name === newName)) {
      i++
      newName = `file${i}.py`
    }
    setFiles([...files, { name: newName, content: '' }])
    setActiveFile(newName)
  }

  const handleFileChange = (value: string | undefined) => {
    setFiles(files.map(f => f.name === activeFile ? { ...f, content: value || '' } : f))
  }

  const handleTabClick = (name: string) => setActiveFile(name)

  const currentFile = files.find(f => f.name === activeFile) || files[0]

  return (
    <div className="app-container" style={{ width: '100%', maxWidth: '1400px', margin: '0 auto', padding: 0 }}>
      <h1>SkoolOfCode Code Editor</h1>
      <div className="editor-panel" style={{ width: '100%', maxWidth: '1400px', margin: '0 auto' }}>
        <div className="file-tabs-bar">
          <div className="file-tabs">
            {files.map(f => (
              <div key={f.name} style={{ display: 'flex', alignItems: 'center' }}>
                <button
                  className={f.name === activeFile ? 'tab active' : 'tab'}
                  onClick={() => handleTabClick(f.name)}
                >
                  {f.name}
                </button>
                {f.name !== 'main.py' && (
                  <button
                    className="tab close-file"
                    title="Close file"
                    onClick={e => {
                      e.stopPropagation();
                      setFiles(files.filter(file => file.name !== f.name));
                      if (activeFile === f.name) {
                        setActiveFile('main.py');
                      }
                    }}
                    style={{
                      background: 'transparent',
                      color: '#fff',
                      border: 'none',
                      fontSize: '1.1em',
                      marginLeft: -8,
                      marginRight: 2,
                      cursor: 'pointer',
                      padding: 0,
                      width: 22,
                      height: 36,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            <button
              className="tab add-file"
              onClick={handleAddFile}
              title="Add File"
            >
              +
            </button>
          </div>
          <div className="editor-actions file-tab-actions">
            <button onClick={runCode} disabled={isRunning}>
              {isRunning ? (
                <>
                  <span className="spinner" style={{
                    display: 'inline-block',
                    width: 16,
                    height: 16,
                    border: '2px solid #ccc',
                    borderTop: '2px solid #646cff',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                    marginRight: 8
                  }} />
                  Executing...
                </>
              ) : 'Run ▶️'}
            </button>
            <button onClick={shareCode}>Share 🔗</button>
            <button onClick={showSnippets}>Snippets 📚</button>
          </div>
        </div>
        <Editor
          height="400px"
          defaultLanguage="python"
          value={currentFile.content}
          onChange={handleFileChange}
          theme="vs-dark"
          options={{ fontSize: 16 }}
        />
        <div className="terminal-panel" style={{ width: '100%', maxWidth: '1400px', margin: '0 auto' }}>
          <div className="terminal-header terminal-header-bg">Terminal</div>
          <div ref={terminalRef} style={{ height: 100, background: '#1a1a1a', padding: 0, textAlign: 'left', fontFamily: 'monospace' }} />
        </div>
      </div>
      <div className="ai-hints">
        <strong>AI Suggestions & Error Hints:</strong>
        <div className="hint-box">Coming soon: Get smart suggestions and error explanations here!</div>
      </div>
    </div>
  )
}

export default App
