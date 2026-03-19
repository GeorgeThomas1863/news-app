export const sendToBack = async (inputParams, method = "POST", raw = false) => {
  const { route } = inputParams;

  try {
    const params = {
      method: method,
      headers: {
        "Content-Type": "application/json",
      },
    };

    if (method !== "GET" && method !== "HEAD") {
      params.body = JSON.stringify(inputParams);
    }

    const res = await fetch(route, params);
    if (!res.ok) return null;
    if (raw) return res;

    //otherwise return json
    const data = await res.json();

    return data;
  } catch (e) {
    // console.log(e);
    return "FAIL";
  }
};
