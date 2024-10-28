const printMessage = message => {
    let chatbox = document.getElementById("chatbox");
    let newMessage = document.createElement("div");
    newMessage.className = "chat";
    newMessage.textContent = message;
    chatbox.appendChild(newMessage);
    chatbox.scrollTop = chatbox.scrollHeight;
};

printMessage('TIP: send /sdn [name] to change your display name');
printMessage('>>> Connecting to server...');

const socket = new WebSocket('ws://139.185.47.36:6969');

socket.onopen = () => {
    printMessage('>>> Connected to server!');
};

// send message from the form
const sendInput = () => {
    let data = this.inputbox.value;
    this.inputbox.value = '';
    let op, msg;

    if (data.length > 0 && data[0] === '/') {
        if (data[1] === '/') {
            op = 'MSG';
            msg = data.slice(1);
        } else {
            op = data.slice(1, 4).toUpperCase();
            msg = data.slice(5);
            if ((data.length >= 5 && data[4] !== ' ') || data.length < 4) {
                printMessage('>>> Invalid command syntax');
                return false;
            }
        }
    } else {
        op = 'MSG';
        msg = data;
    }

    if (op.length === 3 && msg.length > 0) {
        socket.send(op + msg);
    } else {
        console.log(op);
        console.log(msg);
    }
    return false;
}

// message received - show the message in div#chatbox
socket.onmessage = event => {
    let data = event.data;
    let op = data.slice(0, 3);
    let msg = data.slice(3);

    if (op === 'MSG') {
        printMessage(msg);
    } else if (op === 'INV') {
        printMessage('>>> Invalid command: ' + msg);
    } else if (op === 'ACK') {
        // good
    } else {
        printMessage('>>> Unknown opcode [' + op + '] from server');
    }
}

socket.onclose = () => {
    printMessage('>>> Disconnected from server... reload page to reconnect');
}
