

export const waitForAsyncValue = (getValue: () => any, interval=100) => {
  return new Promise((resolve) => {
    const checkInterval = setInterval(() => {
      if (getValue()) {
        clearInterval(checkInterval);
        resolve(true);
      }
    }, interval);
  });
};
