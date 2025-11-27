import axios from "axios";
import type { GraphDTO } from "@/types";

const mock: Record<string, any> = {
  "/api/user/current": { code: 0, data: { id: 1, username: "mock" } },
  "/api/v1/graph/filter": { nodes: [], links: [] } as GraphDTO,
};

const instance = axios.create({
  baseURL: process.env.VUE_APP_API_BASE ?? "http://localhost:8080/api",
  timeout: 5000,
});

export const get = <T>(url: string, params?: object) =>
  instance.get<T>(url, { params }).then((res) => res.data);
export const post = <T>(url: string, data?: object) =>
  instance.post<T>(url, data).then((res) => res.data);
alert(process.env.NODE_ENV);

const myAxios = axios.create({
  // 区分开发和线上环境
  baseURL:
    process.env.NODE_ENV === "development" ? "http://localhost:8080" : "https://codefather.cn",
  timeout: 10000,
  withCredentials: true,
});
// Add a request interceptor
myAxios.interceptors.request.use(
  function (config) {
    // Do something before request is sent
    return config;
  },
  function (error) {
    // Do something with request error
    return Promise.reject(error);
  }
);

// Add a response interceptor
myAxios.interceptors.response.use(
  function (response) {
    // Any status code that lie within the range of 2xx cause this function to trigger
    // Do something with response data
    console.log(response);

    const { data } = response;
    console.log(data);
    // 未登录
    if (data.code === 40100) {
      // 不是获取用户信息接口，或者不是登录页面，则跳转到登录页面
      if (
        !response.request.responseURL.includes("user/current") &&
        !window.location.pathname.includes("/user/login")
      ) {
        window.location.href = `/user/login?redirect=${window.location.href}`;
      }
    }
    return response;
  },
  function (error) {
    // Any status codes that falls outside the range of 2xx cause this function to trigger
    // Do something with response error
    return Promise.reject(error);
  }
);

/* 响应拦截：Mock 优先 */
myAxios.interceptors.response.use(
  (res) => res,
  (error) => {
    const url = error.config?.url ?? "";
    if (mock[url]) {
      return Promise.resolve({
        data: mock[url],
        status: 200,
        statusText: "OK",
        headers: {},
        config: error.config,
      });
    }
    return Promise.reject(error);
  }
);
export default myAxios;
