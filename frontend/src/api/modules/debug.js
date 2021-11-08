import { request } from '../base';

export const fetchHostsBySubscription = request('GET', 'api/debug/fetch_hosts_by_subscription/');
export const fetchSubscriptionDetails = request('GET', 'api/debug/fetch_subscription_details/');
export const fetchSubscriptionsByHost = request('GET', 'api/debug/fetch_subscriptions_by_host/');
export const fetchTaskDetails = request('GET', 'api/debug/fetch_task_details/');

export default {
  fetchHostsBySubscription,
  fetchSubscriptionDetails,
  fetchSubscriptionsByHost,
  fetchTaskDetails,
};
