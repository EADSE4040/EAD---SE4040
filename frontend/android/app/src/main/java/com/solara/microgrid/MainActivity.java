package com.solara.microgrid;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.view.WindowInsets;
import android.widget.*;
import com.google.zxing.BarcodeFormat;
import com.google.zxing.MultiFormatWriter;
import com.google.zxing.common.BitMatrix;
import com.google.zxing.integration.android.IntentIntegrator;
import com.google.zxing.integration.android.IntentResult;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/** Pure native Android UI. All booking, authorization, approval and transfer rules are checked by the C# API. */
public final class MainActivity extends Activity {
    private static final int GREEN=Color.rgb(32,93,70), MUTED=Color.rgb(112,130,118), BACKGROUND=Color.rgb(245,247,241);
    private LocalStore store; private ApiClient api; private JSONObject user;
    private LinearLayout root, content; private TextView message; private ProgressBar progress;
    private String page="Overview"; private int generation=0;
    private final DateTimeFormatter timeFormat=DateTimeFormatter.ofPattern("dd MMM yyyy, HH:mm").withZone(ZoneId.systemDefault());

    @Override public void onCreate(Bundle state) {
        super.onCreate(state); store=new LocalStore(this);
        String url=getPreferences(MODE_PRIVATE).getString("api","http://10.0.2.2:5080/api"); api=new ApiClient(this,url);
        try { String saved=store.readSession(); if(saved!=null) { JSONObject s=new JSONObject(saved); user=s.getJSONObject("user"); api.token=s.getString("token"); } } catch(Exception e) { store.clearSession(); }
        if(user==null) login(); else { shell("Overview"); call("GET","/auth/me",null,(value,error,status)->{ if(error!=null){showError(error);}else{user=(JSONObject)value; dashboard();} }); }
    }
    @Override protected void onDestroy() { api.close(); store.close(); super.onDestroy(); }
    private int dp(int value) { return Math.round(value*getResources().getDisplayMetrics().density); }
    private String encode(String value) { try { return URLEncoder.encode(value,"UTF-8"); } catch(java.io.UnsupportedEncodingException e) { throw new IllegalStateException(e); } }
    private JSONObject json(Object... pairs) { JSONObject object=new JSONObject(); try{for(int i=0;i<pairs.length;i+=2)object.put(pairs[i].toString(),pairs[i+1]);}catch(Exception e){throw new IllegalArgumentException(e);}return object; }
    private String text(JSONObject item,String key) { return item.optString(key,""); }
    private String date(String value) { try{return timeFormat.format(Instant.parse(value));}catch(Exception e){return value;} }
    private boolean operator() { return user!=null && !"Prosumer".equals(text(user,"role")); }
    private GradientDrawable background(int color,int radius) { GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d; }
    private TextView label(String text,int size,int color,boolean bold) { TextView view=new TextView(this);view.setText(text);view.setTextSize(size);view.setTextColor(color);if(bold)view.setTypeface(null,Typeface.BOLD);view.setPadding(0,dp(5),0,dp(5));return view; }
    private Button button(String title,Runnable action) { Button b=new Button(this);b.setText(title);b.setAllCaps(false);b.setTextColor(Color.WHITE);b.setTextSize(14);b.setBackground(background(GREEN,10));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,dp(48));lp.setMargins(0,dp(8),0,dp(8));b.setLayoutParams(lp);b.setOnClickListener(v->action.run());return b; }
    private EditText input(LinearLayout into,String title,int type,String value) { into.addView(label(title,12,MUTED,true));EditText e=new EditText(this);e.setText(value);e.setSingleLine(true);e.setTextSize(14);e.setInputType(type);e.setPadding(dp(12),dp(8),dp(12),dp(8));GradientDrawable bg=background(Color.WHITE,8);bg.setStroke(dp(1),Color.rgb(211,223,207));e.setBackground(bg);LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,dp(48));lp.setMargins(0,0,0,dp(12));e.setLayoutParams(lp);into.addView(e);return e; }
    private LinearLayout card() { LinearLayout c=new LinearLayout(this);c.setOrientation(1);c.setPadding(dp(18),dp(16),dp(18),dp(16));c.setBackground(background(Color.WHITE,12));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.setMargins(0,0,0,dp(14));c.setLayoutParams(lp);content.addView(c);return c; }
    private void shell(String title) {
        generation++; page=title; root=new LinearLayout(this);root.setOrientation(1);root.setBackgroundColor(BACKGROUND);
        root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets;});
        LinearLayout header=new LinearLayout(this);header.setOrientation(1);header.setPadding(dp(22),dp(15),dp(22),dp(15));header.setBackgroundColor(GREEN);
        header.addView(label("☀  solara.",27,Color.WHITE,true));header.addView(label(title,13,Color.rgb(209,226,202),false));root.addView(header);
        progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setIndeterminate(true);progress.setVisibility(View.GONE);root.addView(progress,new LinearLayout.LayoutParams(-1,dp(3)));
        ScrollView scroll=new ScrollView(this);content=new LinearLayout(this);content.setOrientation(1);content.setPadding(dp(20),dp(20),dp(20),dp(20));scroll.addView(content);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        message=label("",13,Color.rgb(158,65,50),false);message.setVisibility(View.GONE);content.addView(message);
        if(user!=null){LinearLayout nav=new LinearLayout(this);nav.setPadding(dp(6),dp(4),dp(6),dp(4));nav.setBackgroundColor(Color.WHITE);
            for(String name:new String[]{"Home","Bookings","Map","More"}){Button b=new Button(this);b.setText(name);b.setAllCaps(false);b.setTextSize(12);b.setTextColor(GREEN);b.setBackgroundColor(Color.WHITE);b.setLayoutParams(new LinearLayout.LayoutParams(0,dp(48),1));b.setOnClickListener(v->{switch(name){case "Home":dashboard();break;case "Bookings":bookings("","");break;case "Map":startActivity(new Intent(this,MapActivity.class).putExtra("token",api.token).putExtra("api",api.baseUrl));break;default:more();}});nav.addView(b);}root.addView(nav);}
        setContentView(root);root.requestApplyInsets();
    }
    private void showError(String error){message.setText(error);message.setVisibility(View.VISIBLE);}
    private void call(String method,String path,JSONObject body,ApiClient.Callback callback) {
        int current=generation;progress.setVisibility(View.VISIBLE);api.call(method,path,body,(value,error,status)->{
            if(current!=generation)return;progress.setVisibility(View.GONE);
            if(status==401 && user!=null){logout();showError("Your session expired. Please sign in again.");return;}
            callback.done(value,error,status);
        });
    }
    private void login() {
        shell("Prosumer & Operator access");LinearLayout c=card();c.addView(label("Welcome back",25,GREEN,true));c.addView(label("Your local energy community, connected.",14,MUTED,false));
        EditText email=input(c,"Email address",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS,""), password=input(c,"Password",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD,"");
        Button submit=button("Sign in",()->{});submit.setOnClickListener(v->{submit.setEnabled(false);call("POST","/auth/login",json("email",email.getText().toString().trim(),"password",password.getText().toString()),(value,error,status)->{
            submit.setEnabled(true);if(error!=null){showError(error);return;}try{JSONObject s=(JSONObject)value;user=s.getJSONObject("user");api.token=s.getString("token");store.saveSession(s.toString());dashboard();}catch(Exception e){user=null;api.token="";store.clearSession();showError("Unable to securely save this session. Please try again.");}
        });});c.addView(submit);c.addView(button("Create prosumer account",this::register));c.addView(button("Connection settings",this::settings));
    }
    private void register() {
        shell("Create your prosumer account");LinearLayout c=card();c.addView(label("Join the solar community",23,GREEN,true));
        EditText nic=input(c,"National Identity Card",InputType.TYPE_CLASS_TEXT,""), name=input(c,"Full name",InputType.TYPE_CLASS_TEXT,""),email=input(c,"Email",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS,""),phone=input(c,"Phone",InputType.TYPE_CLASS_PHONE,""),address=input(c,"Address",InputType.TYPE_CLASS_TEXT,""),password=input(c,"Password (at least 10 characters)",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD,"");
        Button submit=button("Request registration",()->{});submit.setOnClickListener(v->{submit.setEnabled(false);call("POST","/auth/register",json("nic",nic.getText().toString().trim(),"name",name.getText().toString().trim(),"email",email.getText().toString().trim(),"phone",phone.getText().toString().trim(),"address",address.getText().toString().trim(),"password",password.getText().toString()),(value,error,status)->{submit.setEnabled(true);if(error!=null){showError(error);return;}login();new AlertDialog.Builder(this).setTitle("Registration received").setMessage("Your account is pending Backoffice activation. You can sign in once it is approved.").setPositiveButton("OK",null).show();});});c.addView(submit);c.addView(button("Back to sign in",this::login));
    }
    private void dashboard() {
        shell("Overview");content.addView(label("Hello, "+text(user,"name"),25,GREEN,true));content.addView(label("Local energy. Shared possibility.",14,MUTED,false));
        call("GET","/reservations/dashboard",null,(value,error,status)->{if(error!=null){showError(error);content.addView(button("Retry",this::dashboard));return;}JSONObject d=(JSONObject)value;
            for(String[] metric:new String[][]{{"pending","Pending reservations"},{"approvedFuture","Approved upcoming"},{"completed","Completed transfers"},{"activeNodes","Active microgrid nodes"}}){LinearLayout c=card();c.addView(label(String.valueOf(d.optInt(metric[0])),30,GREEN,true));c.addView(label(metric[1],13,MUTED,false));}
            if(!operator())content.addView(button("Reserve an energy slot",()->bookingForm(null)));else content.addView(button("Scan transaction QR",this::scan));
            content.addView(button("View booking history",()->bookings("",""))); });
    }
    private void bookings(String statusFilter,String search) {
        shell("Energy bookings");LinearLayout filter=card();filter.addView(label("Search your bookings",20,GREEN,true));
        EditText query=input(filter,"Booking ID, NIC or station",InputType.TYPE_CLASS_TEXT,search);
        String[] statuses={"All statuses","Pending","Approved","Completed","Cancelled","Rejected","Expired"};Spinner spinner=new Spinner(this);spinner.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,statuses));for(int i=0;i<statuses.length;i++)if(statuses[i].equals(statusFilter))spinner.setSelection(i);filter.addView(spinner);
        filter.addView(button("Apply filters",()->bookings(spinner.getSelectedItemPosition()==0?"":spinner.getSelectedItem().toString(),query.getText().toString().trim())));
        if(!operator())content.addView(button("New reservation",()->bookingForm(null)));
        loadBookings(statusFilter,search,1);
    }
    private void loadBookings(String statusFilter,String search,int number) {
        String query="?pageSize=20&page="+number+"&status="+encode(statusFilter)+"&search="+encode(search);
        call("GET","/reservations"+query,null,(value,error,status)->{if(error!=null){showError(error);return;}JSONObject response=(JSONObject)value;JSONArray items=response.optJSONArray("items");
            if(number==1 && (items==null||items.length()==0)){content.addView(label("No matching bookings. Try different filters.",14,MUTED,false));return;}
            if(items!=null)for(int i=0;i<items.length();i++){JSONObject b=items.optJSONObject(i);LinearLayout c=card();c.addView(label(text(b,"stationName"),19,GREEN,true));c.addView(label(text(b,"status")+" · "+b.optDouble("energyKwh")+" kWh · "+text(b,"direction"),13,MUTED,true));c.addView(label(date(text(b,"start")),13,MUTED,false));if(operator())c.addView(label(text(b,"prosumerName")+" · "+text(b,"prosumerId"),13,MUTED,false));c.addView(button("Booking details",()->summary(b)));
                if(!operator() && java.util.Arrays.asList("Pending","Approved").contains(text(b,"status"))){c.addView(button("Modify booking",()->bookingForm(b)));c.addView(button("Cancel booking",()->new AlertDialog.Builder(this).setTitle("Cancel this booking?").setMessage("The server will check the twelve-hour notice rule.").setNegativeButton("Keep booking",null).setPositiveButton("Cancel booking",(dialog,which)->call("POST","/reservations/"+text(b,"id")+"/cancel",null,(result,err,code)->{if(err!=null)showError(err);else summary((JSONObject)result);})).show()));}
                if("Approved".equals(text(b,"status")) && !operator())c.addView(button("Show transaction QR",()->qr(b)));
            }
            if(number*20<response.optLong("total")){Button more=button("Load more bookings",()->{});more.setOnClickListener(v->{more.setVisibility(View.GONE);loadBookings(statusFilter,search,number+1);});content.addView(more);}
        });
    }
    private void bookingForm(JSONObject booking) {
        shell(booking==null?"Reserve energy":"Modify reservation");content.addView(label("Choose your trading window",23,GREEN,true));
        call("GET","/slots",null,(slotResult,error,status)->{if(error!=null){showError(error);return;}JSONArray slots=(JSONArray)slotResult;store.put("slots",slots.toString());
            call("GET","/stations",null,(nodeResult,nodeError,code)->{if(nodeError!=null){showError(nodeError);return;}JSONArray nodes=(JSONArray)nodeResult;store.put("stations",nodes.toString());
                if(slots.length()==0){content.addView(label("No upcoming slots are published yet.",14,MUTED,false));return;}
                LinearLayout c=card();List<String> labels=new ArrayList<>();for(int i=0;i<slots.length();i++){JSONObject s=slots.optJSONObject(i);String node="Node";for(int j=0;j<nodes.length();j++){JSONObject n=nodes.optJSONObject(j);if(text(n,"id").equals(text(s,"stationId")))node=text(n,"name");}labels.add(node+"\n"+date(text(s,"start"))+" · "+String.format(java.util.Locale.US,"%.2f",s.optDouble("capacityKwh")-s.optDouble("reservedKwh"))+" kWh available");}
                c.addView(label("Available trading slots",12,MUTED,true));Spinner slot=new Spinner(this);slot.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,labels));if(booking!=null)for(int i=0;i<slots.length();i++)if(text(slots.optJSONObject(i),"id").equals(text(booking,"slotId")))slot.setSelection(i);c.addView(slot);
                EditText energy=input(c,"Energy (kWh)",InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL,booking==null?"":String.valueOf(booking.optDouble("energyKwh")));
                c.addView(label("Transfer type",12,MUTED,true));Spinner direction=new Spinner(this);direction.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"Drop off energy","Charging"}));if(booking!=null&&"Charging".equals(text(booking,"direction")))direction.setSelection(1);c.addView(direction);
                Button submit=button(booking==null?"Request reservation":"Save changes",()->{});submit.setOnClickListener(v->{double amount;try{amount=Double.parseDouble(energy.getText().toString());}catch(Exception e){showError("Enter an energy amount.");return;}submit.setEnabled(false);JSONObject body=json("slotId",text(slots.optJSONObject(slot.getSelectedItemPosition()),"id"),"energyKwh",amount,"direction",direction.getSelectedItemPosition()==0?"DropOff":"Charging");call(booking==null?"POST":"PUT","/reservations"+(booking==null?"":"/"+text(booking,"id")),body,(result,err,http)->{submit.setEnabled(true);if(err!=null)showError(err);else summary((JSONObject)result);});});c.addView(submit);
                c.addView(label("Reservations are within seven days. Changes need twelve hours' notice. Updated bookings return to pending approval.",12,MUTED,false));
            });
        });
    }
    private void summary(JSONObject b) {
        shell("Reservation summary");LinearLayout c=card();c.addView(label(text(b,"status"),15,GREEN,true));c.addView(label(text(b,"stationName"),24,GREEN,true));
        for(String[] row:new String[][]{{"Booking ID",text(b,"id")},{"Prosumer",text(b,"prosumerName")},{"Start",date(text(b,"start"))},{"End",date(text(b,"end"))},{"Reserved energy",b.optDouble("energyKwh")+" kWh"},{"Transfer",text(b,"direction")}}){c.addView(label(row[0],11,MUTED,true));c.addView(label(row[1],14,GREEN,false));}
        if(!b.isNull("transferredKwh"))c.addView(label("Transferred: "+b.optDouble("transferredKwh")+" kWh",14,GREEN,true));
        if("Approved".equals(text(b,"status"))&&!operator())c.addView(button("Show secure transaction QR",()->qr(b)));
        c.addView(button("Back to bookings",()->bookings("","")));
    }
    private void qr(JSONObject booking) {
        shell("Transaction QR");call("GET","/reservations/"+text(booking,"id")+"/qr",null,(value,error,status)->{if(error!=null){showError(error);return;}String payload=text((JSONObject)value,"qrCode");LinearLayout c=card();c.addView(label(text(booking,"stationName"),21,GREEN,true));c.addView(label("Present this code to your Grid Operator.",13,MUTED,false));
            try{BitMatrix bits=new MultiFormatWriter().encode(payload,BarcodeFormat.QR_CODE,600,600);Bitmap bitmap=Bitmap.createBitmap(600,600,Bitmap.Config.ARGB_8888);for(int y=0;y<600;y++)for(int x=0;x<600;x++)bitmap.setPixel(x,y,bits.get(x,y)?Color.BLACK:Color.WHITE);ImageView image=new ImageView(this);image.setImageBitmap(bitmap);image.setContentDescription("Secure transaction QR code");image.setAdjustViewBounds(true);c.addView(image,new LinearLayout.LayoutParams(-1,dp(280)));}catch(Exception e){showError("Unable to display QR code. Please reload.");}
            c.addView(label("Valid until "+date(text((JSONObject)value,"expiresAt")),12,MUTED,false));c.addView(button("Back to booking",()->summary(booking)));
        });
    }
    private void more(){shell("Account & tools");LinearLayout c=card();c.addView(label(text(user,"name"),23,GREEN,true));c.addView(label(text(user,"email"),13,MUTED,false));c.addView(label(text(user,"role"),12,MUTED,true));c.addView(button("Edit my profile",this::profile));if(operator()){c.addView(button("Scan transaction QR",this::scan));c.addView(button("Enter transaction payload",()->verifyForm("")));}else c.addView(button("Deactivate my account",()->new AlertDialog.Builder(this).setTitle("Deactivate account?").setMessage("You will be signed out. Only Backoffice can reactivate your account. Existing bookings remain on the server.").setNegativeButton("Keep account",null).setPositiveButton("Deactivate",(d,w)->call("POST","/auth/me/deactivate",null,(value,error,status)->{if(error!=null)showError(error);else logout();})).show()));c.addView(button("Connection settings",this::settings));c.addView(button("Sign out",this::logout));}
    private void profile(){shell("Edit profile");call("GET","/auth/me",null,(value,error,status)->{if(error!=null){showError(error);return;}user=(JSONObject)value;LinearLayout c=card();EditText name=input(c,"Full name",InputType.TYPE_CLASS_TEXT,text(user,"name")),phone=input(c,"Phone",InputType.TYPE_CLASS_PHONE,text(user,"phone")),address=input(c,"Address",InputType.TYPE_CLASS_TEXT,text(user,"address"));c.addView(label("NIC and account role cannot be changed.",12,MUTED,false));Button save=button("Save profile",()->{});save.setOnClickListener(v->{save.setEnabled(false);call("PUT","/auth/me",json("name",name.getText().toString().trim(),"phone",phone.getText().toString().trim(),"address",address.getText().toString().trim()),(result,err,http)->{save.setEnabled(true);if(err!=null){showError(err);return;}user=(JSONObject)result;try{store.saveSession(json("token",api.token,"user",user).toString());}catch(Exception e){showError("Profile saved, but local session could not be updated.");}more();Toast.makeText(this,"Profile updated",Toast.LENGTH_SHORT).show();});});c.addView(save);});}
    private void scan(){if(!operator())return;new IntentIntegrator(this).setDesiredBarcodeFormats(IntentIntegrator.QR_CODE).setPrompt("Scan the prosumer transaction QR").setBeepEnabled(false).setOrientationLocked(false).initiateScan();}
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){super.onActivityResult(requestCode,resultCode,data);IntentResult result=IntentIntegrator.parseActivityResult(requestCode,resultCode,data);if(result!=null&&result.getContents()!=null&&operator())verifyForm(result.getContents());}
    private void verifyForm(String scanned){shell("Verify energy transfer");LinearLayout c=card();c.addView(label("Verify with the server",23,GREEN,true));EditText code=input(c,"Transaction QR payload",InputType.TYPE_CLASS_TEXT,scanned);Button verify=button("Verify transaction",()->{});verify.setOnClickListener(v->{verify.setEnabled(false);call("POST","/reservations/verify",json("qrCode",code.getText().toString().trim()),(value,error,status)->{verify.setEnabled(true);if(error!=null){showError(error);return;}transfer((JSONObject)value,code.getText().toString().trim());});});c.addView(verify);if(!scanned.isEmpty())verify.performClick();}
    private void transfer(JSONObject booking,String qr){shell("Finalize transfer");LinearLayout c=card();c.addView(label(text(booking,"prosumerName"),23,GREEN,true));c.addView(label(text(booking,"stationName")+"\n"+date(text(booking,"start")),14,MUTED,false));c.addView(label("Reserved: "+booking.optDouble("energyKwh")+" kWh · "+text(booking,"direction"),14,GREEN,true));EditText energy=input(c,"Actual transferred energy (kWh)",InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL,String.valueOf(booking.optDouble("energyKwh")));Button complete=button("Complete energy transfer",()->{});complete.setOnClickListener(v->{double amount;try{amount=Double.parseDouble(energy.getText().toString());}catch(Exception e){showError("Enter the transferred energy amount.");return;}new AlertDialog.Builder(this).setTitle("Confirm physical transfer").setMessage("Record "+amount+" kWh as completed? This can only be done once.").setNegativeButton("Back",null).setPositiveButton("Complete",(d,w)->{complete.setEnabled(false);call("POST","/reservations/complete",json("qrCode",qr,"transferredKwh",amount),(value,error,status)->{complete.setEnabled(true);if(error!=null)showError(error);else summary((JSONObject)value);});}).show();});c.addView(complete);}
    private void settings(){LinearLayout form=new LinearLayout(this);form.setOrientation(1);form.setPadding(dp(20),dp(8),dp(20),dp(8));EditText url=input(form,"API address (ends with /api)",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_URI,api.baseUrl);AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Connection settings").setView(form).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();dialog.setOnShowListener(d->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{String value=url.getText().toString().trim().replaceAll("/+$","");try{java.net.URI uri=new java.net.URI(value);if(uri.getHost()==null||(!"https".equals(uri.getScheme())&&!(BuildConfig.DEBUG&&"http".equals(uri.getScheme())))||!uri.getPath().endsWith("/api"))throw new Exception();}catch(Exception e){url.setError("Use an HTTPS API URL ending in /api (HTTP is allowed only in debug builds).");return;}if(!value.equals(api.baseUrl)){api.baseUrl=value;getPreferences(MODE_PRIVATE).edit().putString("api",value).apply();logout();}dialog.dismiss();}));dialog.show();}
    private void logout(){store.clearSession();api.token="";user=null;login();}
}
