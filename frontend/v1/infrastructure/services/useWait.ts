

export const waitForCondition = (getValue: () => any, interval=100) => {
  return new Promise((resolve, reject) => {
    const checkInterval = setInterval(() => {
      if (getValue()) {
        clearInterval(checkInterval);
        resolve(true);
      }
    }, interval);
  });
};
