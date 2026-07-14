import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/papers" },
  {
    path: "/papers",
    name: "Papers",
    component: () => import("../views/papers/PaperLayout.vue"),
  },
  {
    path: "/qa",
    name: "GlobalQA",
    component: () => import("../views/GlobalQA.vue"),
  },
  {
    path: "/admin/review",
    name: "AdminReview",
    component: () => import("../views/admin/ReviewPage.vue"),
  },
];

export default createRouter({ history: createWebHistory(), routes });
