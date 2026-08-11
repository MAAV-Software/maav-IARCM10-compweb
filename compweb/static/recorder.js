let recorder;
let stream;

async function startRecording() {
    console.log("Start button clicked");

    try {
        console.log("Requesting microphone...");

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: true
        });

        console.log("Microphone granted:", stream);

        recorder = new MediaRecorder(stream);

        recorder.ondataavailable = async (event) => {
            await fetch("/record", {
                method: "POST",
                headers: {
                "Content-Type": "application/json"
            },
                body: event.data
            });
        };

        recorder.start(100); // send chunks every 100ms

        console.log("Recording started");

    } catch (err) {
        console.error("Microphone error:", err);
    }

}

function stopRecording() {
    if (recorder && recorder.state !== "inactive") {
        recorder.stop();
    }

    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }

    console.log("Recording stopped");
}

// const pollTimer = setInterval(async () => {
//     const response = await fetch("/speak");
//     const data = await response.json();

//     if (data.message !== "") {
//         const utterance =
//             new SpeechSynthesisUtterance(data.message);

//         speechSynthesis.speak(utterance);

//         if (data.message === "Jarvis is terminating the mission") {
//             clearInterval(pollTimer);
//         }

//         if(data.message === "Jarvis is starting the mission"){
//             clearInterval(pollTimer);
//         }
//     }

// }, 500);