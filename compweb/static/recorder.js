async function sendMessage() {
    const response = await fetch("/record", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            message: "hello flask"
        })
    });

    const result = await response.json();

    console.log(result);
}