// Removed unused executePython function and axios import since only WebSocket is used now.

// Interactive execution using WebSocket
export function executePythonWS(code: string, {
  onStdout,
  onStderr,
  onClose,
}: {
  onStdout: (data: string) => void,
  onStderr: (data: string) => void,
  onClose?: () => void,
}) {
  const ws = new WebSocket('BACKEND_SERVER_URL');
  ws.onopen = () => {
    ws.send(JSON.stringify({ code }));
  };
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'stdout') onStdout(msg.data);
    if (msg.type === 'stderr') onStderr(msg.data);
  };
  ws.onclose = () => { if (onClose) onClose(); };
  // Return a function to send input to the backend
  return (input: string) => {
    ws.send(input);
  };
}