import { request } from '../base';

export const fetchHostsBySubscription = request('GET', 'debug/fetch_hosts_by_subscription/');
export const fetchSubscriptionDetails = request('GET', 'debug/fetch_subscription_details/');
export const fetchSubscriptionsByHost = request('GET', 'debug/fetch_subscriptions_by_host/');
export const fetchTaskDetails = request('GET', 'debug/fetch_task_details/');

export default {
  fetchHostsBySubscription,
  fetchSubscriptionDetails,
  fetchSubscriptionsByHost,
  fetchTaskDetails,
};
