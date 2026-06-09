import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/papers" },
  {
    path: "/papers",
    name: "Papers",
    component: () => import("../views/papers/PaperLayout.vue"),
  },
];

export default createRouter({ history: createWebHistory(), routes });
