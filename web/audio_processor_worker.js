let previousData = [];

onmessage = (event) => {
    const dataArray = event.data;
    if (previousData.length !== dataArray.length) {
        previousData = new Array(dataArray.length).fill(0);
    }

    const smoothedData = dataArray.map((value, index) => {
        const smoothed = (value * 0.3) + (previousData[index] * 0.7);
        previousData[index] = smoothed;
        return smoothed;
    });

    postMessage(smoothedData);
};
