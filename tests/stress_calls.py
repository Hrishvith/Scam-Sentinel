"""Wider phrasing check, 10 Nov 2026: synthetic scam and everyday call lines in English, Hindi (incl. Hinglish)
and Kannada. TUNING was used to add rules; FRESH was written afterwards and scored 18/24 scams before its own
misses were fixed, so neither is unseen any more. REVIEW kn/hi wording with native speakers."""

TUNING_SCAMS = {
 "en": [
  "Sir this is from the Telecom Regulatory Authority, your SIM card will be deactivated in two hours because it is linked to illegal activity. Press 9 to speak to the officer.",
  "This is Mumbai cyber police. Your Aadhaar is used in a money laundering case. You are under digital arrest, stay on video call and do not tell your family.",
  "Hello madam, I am calling from FedEx. A parcel in your name has five fake passports and drugs. I will connect you to the narcotics department.",
  "Your electricity connection will be cut tonight at 9:30 because the last bill is not updated. Call this number and pay immediately.",
  "Congratulations, you have won twenty five lakh rupees in the KBC lucky draw. To claim the prize pay a processing fee of ten thousand.",
  "Sir your credit card reward points of 8,500 will expire today. Tell me the OTP you just got to redeem them into cash.",
  "Hi, I am from the HR team, we have a part time job, you earn 3000 a day by liking videos. First you pay 1000 rupees registration through UPI.",
  "Your loan is approved instantly, just pay the insurance charge of 4,999 rupees first and download our loan app from this link.",
  "Mom, I lost my phone, this is my friend's number. I am in trouble, please send 20,000 to this UPI ID urgently, don't tell dad.",
  "Uncle, your son had an accident, he is in the hospital, the doctor needs fifty thousand for the operation right now, send it to me.",
  "I am calling from your bank's fraud department. Someone is trying to take money from your account. To block it, read me the code we just sent.",
  "Your KYC is pending, your account will be frozen today. Click the link I sent by SMS and enter your card details.",
  "This is customer care. To get your refund, install the Quick Support app and give me the number shown on the screen.",
  "We are from the income tax department, you have a refund of 15,000. Please share your net banking password to process it.",
  "Invest in our crypto trading group, you will get double returns in one week, guaranteed profit, send money to this account.",
  "I am an army officer, I want to buy your sofa. I will send money by Google Pay, just scan the QR code I send and enter your PIN to receive it.",
  "Your Amazon order of an iPhone is placed. If you did not order it, press 1. Now to cancel, tell me your card number and CVV.",
  "Sir this is a CBI officer speaking, there is an arrest warrant in your name, transfer your savings to an RBI verification account for checking, it will be refunded."
 ],
 "hi": [
  "मैं ट्राई से बोल रहा हूँ, आपका सिम कार्ड दो घंटे में बंद हो जाएगा क्योंकि इस नंबर से गैरकानूनी काम हुआ है।",
  "मुंबई साइबर पुलिस से बोल रहा हूँ, आपके आधार से मनी लॉन्ड्रिंग हुई है, आप डिजिटल अरेस्ट में हैं, वीडियो कॉल पर रहिए और घर पर किसी को मत बताइए।",
  "मैडम, फेडेक्स कूरियर से बोल रहा हूँ, आपके नाम के पार्सल में ड्रग्स मिले हैं, मैं आपको नारकोटिक्स विभाग से जोड़ता हूँ।",
  "आपकी बिजली आज रात साढ़े नौ बजे काट दी जाएगी, पिछला बिल अपडेट नहीं है, तुरंत इस नंबर पर पेमेंट कीजिए।",
  "बधाई हो, आपने केबीसी लकी ड्रॉ में पच्चीस लाख जीते हैं, इनाम लेने के लिए दस हज़ार प्रोसेसिंग फीस भरिए।",
  "सर, आपके क्रेडिट कार्ड के रिवॉर्ड पॉइंट्स आज खत्म हो जाएंगे, अभी जो ओटीपी आया है वो बोलिए।",
  "घर बैठे पार्ट टाइम जॉब है, वीडियो लाइक करके रोज़ तीन हज़ार कमाइए, पहले एक हज़ार रजिस्ट्रेशन फीस यूपीआई से भेजिए।",
  "मम्मी, मेरा फोन खो गया, ये दोस्त का नंबर है, मुसीबत में हूँ, बीस हज़ार इस यूपीआई पर अभी भेज दो, पापा को मत बताना।",
  "अंकल, आपके बेटे का एक्सीडेंट हो गया है, अस्पताल में है, ऑपरेशन के लिए पचास हज़ार तुरंत भेजिए।",
  "मैं बैंक के फ्रॉड डिपार्टमेंट से बोल रहा हूँ, कोई आपके खाते से पैसे निकाल रहा है, रोकने के लिए अभी आया कोड पढ़कर सुनाइए।",
  "आपका केवाईसी पेंडिंग है, आज आपका खाता बंद हो जाएगा, मैसेज में भेजे लिंक पर क्लिक करके कार्ड की डिटेल डालिए।",
  "रिफंड के लिए क्विक सपोर्ट ऐप डाउनलोड कीजिए और स्क्रीन पर जो नंबर दिख रहा है वो मुझे बताइए।",
  "इनकम टैक्स विभाग से बोल रहे हैं, आपका पंद्रह हज़ार का रिफंड है, नेट बैंकिंग पासवर्ड बताइए।",
  "हमारे क्रिप्टो ग्रुप में पैसा लगाइए, एक हफ्ते में डबल, पक्का मुनाफा, इस खाते में पैसे ट्रांसफर कीजिए।",
  "मैं आर्मी में हूँ, आपका सोफा खरीदना है, गूगल पे से पैसे भेजता हूँ, बस मेरा भेजा क्यूआर कोड स्कैन करके पिन डाल दीजिए।",
  "सीबीआई अफसर बोल रहा हूँ, आपके नाम पर गिरफ्तारी वारंट है, अपनी सारी बचत आरबीआई वेरिफिकेशन खाते में ट्रांसफर कीजिए।",
  "bhai main police se bol raha hoon, aapke bete ko pakda hai, case band karna hai to abhi paise bhejo, kisi ko mat batana",
  "sir aapka account block ho jayega, abhi jo otp aaya hai wo batao jaldi"
 ],
 "kn": [
  "ನಾನು ಟ್ರಾಯ್‌ನಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ, ನಿಮ್ಮ ಸಿಮ್ ಕಾರ್ಡ್ ಎರಡು ಗಂಟೆಯಲ್ಲಿ ಬ್ಲಾಕ್ ಆಗುತ್ತದೆ, ಈ ನಂಬರ್‌ನಿಂದ ಅಕ್ರಮ ಚಟುವಟಿಕೆ ನಡೆದಿದೆ.",
  "ಮುಂಬೈ ಸೈಬರ್ ಪೊಲೀಸ್ ಮಾತನಾಡುತ್ತಿದ್ದೇವೆ, ನಿಮ್ಮ ಆಧಾರ್ ಹಣ ವರ್ಗಾವಣೆ ಕೇಸ್‌ನಲ್ಲಿ ಇದೆ, ನೀವು ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್‌ನಲ್ಲಿದ್ದೀರಿ, ವಿಡಿಯೋ ಕಾಲ್‌ನಲ್ಲೇ ಇರಿ, ಮನೆಯವರಿಗೆ ಹೇಳಬೇಡಿ.",
  "ಮೇಡಂ, ಫೆಡೆಕ್ಸ್ ಕೊರಿಯರ್‌ನಿಂದ ಕರೆ, ನಿಮ್ಮ ಹೆಸರಿನ ಪಾರ್ಸೆಲ್‌ನಲ್ಲಿ ಡ್ರಗ್ಸ್ ಸಿಕ್ಕಿದೆ, ನಾರ್ಕೋಟಿಕ್ಸ್ ವಿಭಾಗಕ್ಕೆ ಕನೆಕ್ಟ್ ಮಾಡುತ್ತೇನೆ.",
  "ನಿಮ್ಮ ಕರೆಂಟ್ ಕನೆಕ್ಷನ್ ಇಂದು ರಾತ್ರಿ ಕಟ್ ಆಗುತ್ತದೆ, ಹಿಂದಿನ ಬಿಲ್ ಅಪ್‌ಡೇಟ್ ಆಗಿಲ್ಲ, ತಕ್ಷಣ ಈ ನಂಬರ್‌ಗೆ ಹಣ ಕಟ್ಟಿ.",
  "ಅಭಿನಂದನೆಗಳು, ನೀವು ಲಕ್ಕಿ ಡ್ರಾದಲ್ಲಿ ಇಪ್ಪತ್ತೈದು ಲಕ್ಷ ಗೆದ್ದಿದ್ದೀರಿ, ಬಹುಮಾನ ಪಡೆಯಲು ಹತ್ತು ಸಾವಿರ ಪ್ರೊಸೆಸಿಂಗ್ ಫೀಸ್ ಕಟ್ಟಿ.",
  "ಸರ್, ನಿಮ್ಮ ಕ್ರೆಡಿಟ್ ಕಾರ್ಡ್ ರಿವಾರ್ಡ್ ಪಾಯಿಂಟ್ಸ್ ಇಂದು ಮುಗಿಯುತ್ತವೆ, ಈಗ ಬಂದ ಒಟಿಪಿ ಹೇಳಿ.",
  "ಮನೆಯಿಂದಲೇ ಪಾರ್ಟ್ ಟೈಮ್ ಕೆಲಸ, ವಿಡಿಯೋ ಲೈಕ್ ಮಾಡಿ ದಿನಕ್ಕೆ ಮೂರು ಸಾವಿರ ಗಳಿಸಿ, ಮೊದಲು ಸಾವಿರ ರೂಪಾಯಿ ನೋಂದಣಿ ಶುಲ್ಕ ಯುಪಿಐ ಮೂಲಕ ಕಳುಹಿಸಿ.",
  "ಅಮ್ಮಾ, ನನ್ನ ಫೋನ್ ಕಳೆದುಹೋಯಿತು, ಇದು ಸ್ನೇಹಿತನ ನಂಬರ್, ತೊಂದರೆಯಲ್ಲಿದ್ದೇನೆ, ಇಪ್ಪತ್ತು ಸಾವಿರ ಈ ಯುಪಿಐಗೆ ಈಗಲೇ ಕಳುಹಿಸು, ಅಪ್ಪನಿಗೆ ಹೇಳಬೇಡ.",
  "ಅಂಕಲ್, ನಿಮ್ಮ ಮಗನಿಗೆ ಆಕ್ಸಿಡೆಂಟ್ ಆಗಿದೆ, ಆಸ್ಪತ್ರೆಯಲ್ಲಿದ್ದಾನೆ, ಆಪರೇಷನ್‌ಗೆ ಐವತ್ತು ಸಾವಿರ ತಕ್ಷಣ ಕಳುಹಿಸಿ.",
  "ನಾನು ಬ್ಯಾಂಕಿನ ಫ್ರಾಡ್ ವಿಭಾಗದಿಂದ ಕರೆ ಮಾಡುತ್ತಿದ್ದೇನೆ, ಯಾರೋ ನಿಮ್ಮ ಖಾತೆಯಿಂದ ಹಣ ತೆಗೆಯುತ್ತಿದ್ದಾರೆ, ತಡೆಯಲು ಈಗ ಬಂದ ಕೋಡ್ ಓದಿ.",
  "ನಿಮ್ಮ ಕೆವೈಸಿ ಬಾಕಿ ಇದೆ, ಇಂದು ನಿಮ್ಮ ಖಾತೆ ಬ್ಲಾಕ್ ಆಗುತ್ತದೆ, ಮೆಸೇಜ್‌ನಲ್ಲಿರುವ ಲಿಂಕ್ ಒತ್ತಿ ಕಾರ್ಡ್ ವಿವರ ಹಾಕಿ.",
  "ರಿಫಂಡ್‌ಗಾಗಿ ಎನಿಡೆಸ್ಕ್ ಆ್ಯಪ್ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ, ಸ್ಕ್ರೀನ್‌ನಲ್ಲಿ ಕಾಣುವ ನಂಬರ್ ನನಗೆ ಹೇಳಿ.",
  "ಆದಾಯ ತೆರಿಗೆ ಇಲಾಖೆಯಿಂದ ಕರೆ, ನಿಮಗೆ ಹದಿನೈದು ಸಾವಿರ ರಿಫಂಡ್ ಇದೆ, ನೆಟ್ ಬ್ಯಾಂಕಿಂಗ್ ಪಾಸ್ವರ್ಡ್ ತಿಳಿಸಿ.",
  "ನಮ್ಮ ಕ್ರಿಪ್ಟೋ ಗ್ರೂಪ್‌ನಲ್ಲಿ ಹಣ ಹಾಕಿ, ಒಂದು ವಾರದಲ್ಲಿ ಡಬಲ್, ಗ್ಯಾರಂಟಿ ಲಾಭ, ಈ ಖಾತೆಗೆ ಹಣ ಟ್ರಾನ್ಸ್‌ಫರ್ ಮಾಡಿ.",
  "ನಾನು ಆರ್ಮಿಯಲ್ಲಿದ್ದೇನೆ, ನಿಮ್ಮ ಸೋಫಾ ಕೊಳ್ಳುತ್ತೇನೆ, ಗೂಗಲ್ ಪೇ ಮೂಲಕ ಹಣ ಕಳುಹಿಸುತ್ತೇನೆ, ನಾನು ಕಳುಹಿಸುವ ಕ್ಯೂಆರ್ ಕೋಡ್ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ ಪಿನ್ ಹಾಕಿ.",
  "ಸಿಬಿಐ ಅಧಿಕಾರಿ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ, ನಿಮ್ಮ ಹೆಸರಿನಲ್ಲಿ ಅರೆಸ್ಟ್ ವಾರೆಂಟ್ ಇದೆ, ನಿಮ್ಮ ಉಳಿತಾಯದ ಹಣವನ್ನು ಆರ್‌ಬಿಐ ವೆರಿಫಿಕೇಶನ್ ಖಾತೆಗೆ ವರ್ಗಾಯಿಸಿ.",
  "ಸರ್ ನಿಮ್ಮ ಅಕೌಂಟ್ ಬ್ಲಾಕ್ ಆಗುತ್ತೆ, ಈಗ ಬಂದಿರೋ ಓಟಿಪಿ ಬೇಗ ಹೇಳಿ"
 ]
}
TUNING_NORMAL = {
 "en": [
  "Hi, this is Dr. Rao's clinic, your appointment is confirmed for tomorrow at 11 am. Please bring your old reports.",
  "Hello, I am the delivery executive from Amazon, I am at your gate, please share the delivery OTP to hand over the parcel.",
  "This is SBI fraud monitoring. Did you just make a payment of 2,000 rupees at a petrol pump? If not, please call the number on the back of your card. We will never ask for your OTP.",
  "Good morning, this is a reminder that your electricity bill of 1,240 rupees is due on the 15th. You can pay at the BESCOM website or office.",
  "Hello, this is the police station, we are calling for your passport verification. Please come to the station with your Aadhaar card tomorrow.",
  "Hey, are we still meeting for lunch on Sunday? Let me know so I can book the table.",
  "Sir, we are offering a home loan at 8.5 percent interest. If you are interested, visit our nearest branch with your documents.",
  "Your courier could not be delivered today because nobody was at home. We will try again tomorrow between 10 and 2.",
  "Grandma, I reached the hostel safely. Exams start next week, I will call you on Sunday.",
  "This is a message from Bengaluru city police: if anyone calls claiming to be from CBI or customs and asks for money, it is a scam. Hang up and call 1930.",
  "Your OTP for logging into the app is 4 5 6 7. Do not share it with anyone.",
  "Hello sir, I am calling from the school. Tomorrow is a holiday because of the festival."
 ],
 "hi": [
  "नमस्ते, डॉक्टर शर्मा क्लिनिक से बोल रहे हैं, कल सुबह ग्यारह बजे आपका अपॉइंटमेंट पक्का है।",
  "मैं अमेज़न से डिलीवरी वाला हूँ, गेट पर खड़ा हूँ, पार्सल देने के लिए डिलीवरी ओटीपी बता दीजिए।",
  "बैंक की फ्रॉड मॉनिटरिंग से कॉल है, क्या आपने अभी दो हज़ार का पेमेंट किया? नहीं किया तो कार्ड के पीछे लिखे नंबर पर कॉल करें, हम कभी ओटीपी नहीं मांगते।",
  "आपका बिजली का बिल बारह सौ चालीस रुपये है, पंद्रह तारीख तक वेबसाइट या दफ्तर में जमा कर दीजिए।",
  "थाने से बोल रहे हैं, पासपोर्ट वेरिफिकेशन के लिए कल आधार कार्ड लेकर थाने आ जाइए।",
  "अरे, रविवार को खाने पर मिल रहे हैं ना? बता देना, मैं टेबल बुक कर दूँगा।",
  "आपका कूरियर आज नहीं पहुँच सका क्योंकि घर पर कोई नहीं था, कल फिर आएंगे।",
  "दादी, मैं हॉस्टल पहुँच गया हूँ, अगले हफ्ते परीक्षा है, रविवार को फोन करूँगा।",
  "पुलिस की सूचना: अगर कोई सीबीआई या कस्टम्स बनकर पैसे मांगे तो यह धोखा है, फोन काटें और 1930 पर कॉल करें।",
  "अपना ओटीपी किसी को भी न दें, बैंक कर्मचारी को भी नहीं।",
  "sir kal school band rahega tyohar ki wajah se",
  "beta ghar kab aa rahe ho, mummy ne khana banaya hai"
 ],
 "kn": [
  "ನಮಸ್ಕಾರ, ಡಾಕ್ಟರ್ ರಾವ್ ಕ್ಲಿನಿಕ್‌ನಿಂದ ಕರೆ, ನಾಳೆ ಬೆಳಿಗ್ಗೆ ಹನ್ನೊಂದು ಗಂಟೆಗೆ ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಖಚಿತವಾಗಿದೆ.",
  "ನಾನು ಅಮೆಜಾನ್ ಡೆಲಿವರಿ ಹುಡುಗ, ಗೇಟ್ ಹತ್ತಿರ ಇದ್ದೇನೆ, ಪಾರ್ಸೆಲ್ ಕೊಡಲು ಡೆಲಿವರಿ ಒಟಿಪಿ ಹೇಳಿ.",
  "ಬ್ಯಾಂಕ್‌ನ ಫ್ರಾಡ್ ಮಾನಿಟರಿಂಗ್‌ನಿಂದ ಕರೆ, ನೀವು ಈಗ ಎರಡು ಸಾವಿರ ಪಾವತಿ ಮಾಡಿದ್ರಾ? ಇಲ್ಲದಿದ್ದರೆ ಕಾರ್ಡ್ ಹಿಂದಿರುವ ನಂಬರ್‌ಗೆ ಕರೆ ಮಾಡಿ, ನಾವು ಎಂದಿಗೂ ಒಟಿಪಿ ಕೇಳುವುದಿಲ್ಲ.",
  "ನಿಮ್ಮ ಕರೆಂಟ್ ಬಿಲ್ ಸಾವಿರದ ಇನ್ನೂರ ನಲವತ್ತು ರೂಪಾಯಿ, ಹದಿನೈದನೇ ತಾರೀಖಿನೊಳಗೆ ಬೆಸ್ಕಾಂ ವೆಬ್‌ಸೈಟ್ ಅಥವಾ ಕಚೇರಿಯಲ್ಲಿ ಕಟ್ಟಿ.",
  "ಪೊಲೀಸ್ ಠಾಣೆಯಿಂದ ಕರೆ, ಪಾಸ್‌ಪೋರ್ಟ್ ವೆರಿಫಿಕೇಶನ್‌ಗೆ ನಾಳೆ ಆಧಾರ್ ಕಾರ್ಡ್ ತೆಗೆದುಕೊಂಡು ಠಾಣೆಗೆ ಬನ್ನಿ.",
  "ಭಾನುವಾರ ಊಟಕ್ಕೆ ಸಿಗೋಣ ಅಲ್ವಾ? ಹೇಳು, ನಾನು ಟೇಬಲ್ ಬುಕ್ ಮಾಡ್ತೀನಿ.",
  "ಇಂದು ಮನೆಯಲ್ಲಿ ಯಾರೂ ಇರಲಿಲ್ಲ, ಹಾಗಾಗಿ ನಿಮ್ಮ ಕೊರಿಯರ್ ಕೊಡಲು ಆಗಲಿಲ್ಲ, ನಾಳೆ ಮತ್ತೆ ಬರುತ್ತೇವೆ.",
  "ಅಜ್ಜಿ, ನಾನು ಹಾಸ್ಟೆಲ್ ತಲುಪಿದೆ, ಮುಂದಿನ ವಾರ ಪರೀಕ್ಷೆ, ಭಾನುವಾರ ಕರೆ ಮಾಡುತ್ತೇನೆ.",
  "ಪೊಲೀಸ್ ಸೂಚನೆ: ಯಾರಾದರೂ ಸಿಬಿಐ ಅಥವಾ ಕಸ್ಟಮ್ಸ್ ಎಂದು ಹೇಳಿ ಹಣ ಕೇಳಿದರೆ ಅದು ಮೋಸ, ಕರೆ ಕಟ್ ಮಾಡಿ 1930 ಗೆ ಕರೆ ಮಾಡಿ.",
  "ನಿಮ್ಮ ಒಟಿಪಿ ಯಾರಿಗೂ ಕೊಡಬೇಡಿ, ಬ್ಯಾಂಕ್ ಸಿಬ್ಬಂದಿಗೂ ಸಹ.",
  "ನಾಳೆ ಹಬ್ಬದ ಪ್ರಯುಕ್ತ ಶಾಲೆಗೆ ರಜೆ ಇದೆ.",
  "ಮಗನೇ, ಯಾವಾಗ ಮನೆಗೆ ಬರ್ತೀಯಾ? ಅಮ್ಮ ಊಟ ಮಾಡಿದ್ದಾರೆ."
 ]
}

FRESH_SCAMS = {
 "en": [
  "Hello, I am Inspector Sharma from Delhi crime branch. Your mobile number was used to harass women. A case has been filed, you must cooperate or you will be arrested.",
  "Madam, your HDFC debit card is blocked. I will unblock it now, just tell me the 6 digit number you received by SMS.",
  "This is BSNL, your SIM KYC is expired, your number will be blocked in 24 hours. Download the app I send you to update.",
  "You have been selected for a work from home job with Amazon. Pay 2,500 rupees security deposit to get your joining kit.",
  "Grandpa it's me, I got into a fight and the police took me. Please send 30,000 for bail, and please don't tell mom.",
  "Sir, your gas connection subsidy refund of 5,000 is ready. Share the PIN of your UPI so we can credit it.",
  "I am calling from customs. Your gift parcel from London has foreign currency, pay the clearance charge of 45,000 immediately or face legal action.",
  "Your PAN card is not linked, your bank account will be suspended today. Click the link and fill your details."
 ],
 "hi": [
  "मैं दिल्ली क्राइम ब्रांच से इंस्पेक्टर शर्मा बोल रहा हूँ, आपके नंबर पर केस दर्ज हुआ है, सहयोग नहीं किया तो गिरफ्तार कर लेंगे।",
  "मैडम, आपका डेबिट कार्ड ब्लॉक हो गया है, अनब्लॉक करने के लिए एसएमएस में आया छह अंकों का नंबर बताइए।",
  "बीएसएनएल से बोल रहे हैं, आपकी सिम का केवाईसी खत्म हो गया है, चौबीस घंटे में नंबर बंद हो जाएगा, मैं जो ऐप भेजूँ उसे डाउनलोड कीजिए।",
  "आपका अमेज़न में वर्क फ्रॉम होम जॉब के लिए सेलेक्शन हुआ है, जॉइनिंग किट के लिए ढाई हज़ार सिक्योरिटी डिपॉज़िट भेजिए।",
  "नानाजी, मैं हूँ, झगड़े में पुलिस ने पकड़ लिया है, ज़मानत के लिए तीस हज़ार भेज दीजिए, मम्मी को मत बताना।",
  "सर, आपकी गैस सब्सिडी का पाँच हज़ार रिफंड तैयार है, क्रेडिट करने के लिए अपना यूपीआई पिन बताइए।",
  "कस्टम्स से बोल रहा हूँ, लंदन से आए आपके गिफ्ट पार्सल में विदेशी करेंसी है, पैंतालीस हज़ार क्लीयरेंस चार्ज तुरंत भरिए वरना कानूनी कार्रवाई होगी।",
  "आपका पैन लिंक नहीं है, आज आपका बैंक खाता बंद हो जाएगा, लिंक पर क्लिक करके अपनी डिटेल भरिए।"
 ],
 "kn": [
  "ನಾನು ದೆಹಲಿ ಕ್ರೈಂ ಬ್ರಾಂಚ್‌ನ ಇನ್ಸ್ಪೆಕ್ಟರ್ ಶರ್ಮಾ, ನಿಮ್ಮ ನಂಬರ್ ಮೇಲೆ ಕೇಸ್ ದಾಖಲಾಗಿದೆ, ಸಹಕರಿಸದಿದ್ದರೆ ಅರೆಸ್ಟ್ ಮಾಡುತ್ತೇವೆ.",
  "ಮೇಡಂ, ನಿಮ್ಮ ಡೆಬಿಟ್ ಕಾರ್ಡ್ ಬ್ಲಾಕ್ ಆಗಿದೆ, ಅನ್‌ಬ್ಲಾಕ್ ಮಾಡಲು ಎಸ್‌ಎಂಎಸ್‌ನಲ್ಲಿ ಬಂದ ಆರು ಅಂಕಿಯ ನಂಬರ್ ಹೇಳಿ.",
  "ಬಿಎಸ್ಎನ್ಎಲ್‌ನಿಂದ ಕರೆ, ನಿಮ್ಮ ಸಿಮ್ ಕೆವೈಸಿ ಮುಗಿದಿದೆ, ಇಪ್ಪತ್ತನಾಲ್ಕು ಗಂಟೆಯಲ್ಲಿ ನಂಬರ್ ಬ್ಲಾಕ್ ಆಗುತ್ತದೆ, ನಾನು ಕಳುಹಿಸುವ ಆ್ಯಪ್ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ.",
  "ಅಮೆಜಾನ್‌ನಲ್ಲಿ ಮನೆಯಿಂದಲೇ ಕೆಲಸಕ್ಕೆ ನೀವು ಆಯ್ಕೆಯಾಗಿದ್ದೀರಿ, ಜಾಯಿನಿಂಗ್ ಕಿಟ್‌ಗಾಗಿ ಎರಡೂವರೆ ಸಾವಿರ ಸೆಕ್ಯುರಿಟಿ ಡೆಪಾಸಿಟ್ ಕಳುಹಿಸಿ.",
  "ತಾತ, ನಾನು, ಜಗಳದಲ್ಲಿ ಪೊಲೀಸರು ಹಿಡಿದಿದ್ದಾರೆ, ಜಾಮೀನಿಗೆ ಮೂವತ್ತು ಸಾವಿರ ಕಳುಹಿಸಿ, ಅಮ್ಮನಿಗೆ ಹೇಳಬೇಡಿ.",
  "ಸರ್, ನಿಮ್ಮ ಗ್ಯಾಸ್ ಸಬ್ಸಿಡಿ ಐದು ಸಾವಿರ ರಿಫಂಡ್ ಸಿದ್ಧವಾಗಿದೆ, ಜಮಾ ಮಾಡಲು ನಿಮ್ಮ ಯುಪಿಐ ಪಿನ್ ಹೇಳಿ.",
  "ಕಸ್ಟಮ್ಸ್‌ನಿಂದ ಕರೆ, ಲಂಡನ್‌ನಿಂದ ಬಂದ ನಿಮ್ಮ ಗಿಫ್ಟ್ ಪಾರ್ಸೆಲ್‌ನಲ್ಲಿ ವಿದೇಶಿ ಹಣ ಇದೆ, ನಲವತ್ತೈದು ಸಾವಿರ ಕ್ಲಿಯರೆನ್ಸ್ ಚಾರ್ಜ್ ತಕ್ಷಣ ಕಟ್ಟಿ.",
  "ನಿಮ್ಮ ಪ್ಯಾನ್ ಲಿಂಕ್ ಆಗಿಲ್ಲ, ಇಂದು ನಿಮ್ಮ ಬ್ಯಾಂಕ್ ಖಾತೆ ಬ್ಲಾಕ್ ಆಗುತ್ತದೆ, ಲಿಂಕ್ ಒತ್ತಿ ನಿಮ್ಮ ವಿವರ ತುಂಬಿ."
 ]
}
FRESH_NORMAL = {
 "en": [
  "Hi, this is your insurance agent, your policy renewal is due next month, I will drop the form at your house.",
  "Sir, your car service is complete, you can pick it up after 5 pm, the bill is 3,200 rupees.",
  "This is the bank. Your new debit card has been dispatched by post. Never share your card PIN with anyone.",
  "Hello beta, papa here, I reached the hospital for my eye checkup, the doctor says everything is fine.",
  "The police constable is calling about the theft complaint you filed, please come and collect the FIR copy.",
  "Your Swiggy order is on the way, the delivery partner will reach in 10 minutes.",
  "Reminder: your child's school fee is due by Friday, you can pay at the school office.",
  "Hi, I am from the society office, water supply will be off tomorrow from 10 to 2 for repairs."
 ],
 "hi": [
  "नमस्ते, मैं आपका बीमा एजेंट बोल रहा हूँ, अगले महीने पॉलिसी रिन्यू करनी है, फॉर्म घर दे जाऊँगा।",
  "सर, आपकी गाड़ी की सर्विस हो गई है, शाम पाँच बजे के बाद ले जाइए, बिल बत्तीस सौ रुपये है।",
  "बैंक से बोल रहे हैं, आपका नया डेबिट कार्ड डाक से भेज दिया है, अपना पिन कभी किसी को न बताएं।",
  "बेटा, पापा बोल रहा हूँ, आँखों की जाँच के लिए अस्पताल पहुँच गया, डॉक्टर ने कहा सब ठीक है।",
  "थाने से सिपाही बोल रहा हूँ, आपकी चोरी की शिकायत की एफआईआर कॉपी ले जाइए।",
  "आपका स्विगी ऑर्डर रास्ते में है, डिलीवरी वाला दस मिनट में पहुँचेगा।",
  "याद दिला दें, बच्चे की स्कूल फीस शुक्रवार तक स्कूल ऑफिस में जमा करनी है।",
  "सोसाइटी ऑफिस से बोल रहे हैं, कल दस से दो बजे तक पानी नहीं आएगा।"
 ],
 "kn": [
  "ನಮಸ್ಕಾರ, ನಾನು ನಿಮ್ಮ ವಿಮಾ ಏಜೆಂಟ್, ಮುಂದಿನ ತಿಂಗಳು ಪಾಲಿಸಿ ನವೀಕರಣ ಇದೆ, ಫಾರ್ಮ್ ಮನೆಗೆ ತಂದು ಕೊಡುತ್ತೇನೆ.",
  "ಸರ್, ನಿಮ್ಮ ಕಾರ್ ಸರ್ವೀಸ್ ಮುಗಿದಿದೆ, ಸಂಜೆ ಐದರ ನಂತರ ತೆಗೆದುಕೊಂಡು ಹೋಗಿ, ಬಿಲ್ ಮೂರು ಸಾವಿರದ ಇನ್ನೂರು ರೂಪಾಯಿ.",
  "ಬ್ಯಾಂಕ್‌ನಿಂದ ಕರೆ, ನಿಮ್ಮ ಹೊಸ ಡೆಬಿಟ್ ಕಾರ್ಡ್ ಅಂಚೆ ಮೂಲಕ ಕಳುಹಿಸಲಾಗಿದೆ, ನಿಮ್ಮ ಪಿನ್ ಯಾರಿಗೂ ಹೇಳಬೇಡಿ.",
  "ಮಗನೇ, ಅಪ್ಪ ಮಾತಾಡ್ತಿದ್ದೀನಿ, ಕಣ್ಣಿನ ಪರೀಕ್ಷೆಗೆ ಆಸ್ಪತ್ರೆಗೆ ಬಂದಿದ್ದೇನೆ, ಡಾಕ್ಟರ್ ಎಲ್ಲಾ ಸರಿ ಇದೆ ಅಂದರು.",
  "ಠಾಣೆಯಿಂದ ಪೇದೆ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ, ನೀವು ಕೊಟ್ಟ ಕಳ್ಳತನದ ದೂರಿನ ಎಫ್‌ಐಆರ್ ಪ್ರತಿ ತೆಗೆದುಕೊಂಡು ಹೋಗಿ.",
  "ನಿಮ್ಮ ಸ್ವಿಗ್ಗಿ ಆರ್ಡರ್ ದಾರಿಯಲ್ಲಿದೆ, ಡೆಲಿವರಿ ಹುಡುಗ ಹತ್ತು ನಿಮಿಷದಲ್ಲಿ ಬರುತ್ತಾನೆ.",
  "ನೆನಪಿಸುತ್ತಿದ್ದೇವೆ, ಮಗುವಿನ ಶಾಲಾ ಶುಲ್ಕ ಶುಕ್ರವಾರದೊಳಗೆ ಶಾಲೆಯ ಕಚೇರಿಯಲ್ಲಿ ಕಟ್ಟಬೇಕು.",
  "ಸೊಸೈಟಿ ಕಚೇರಿಯಿಂದ ಕರೆ, ನಾಳೆ ಹತ್ತರಿಂದ ಎರಡರವರೆಗೆ ನೀರು ಬರುವುದಿಲ್ಲ."
 ]
}
